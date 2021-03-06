from collections import Counter

import numpy as np

import utils.array_utils as au
import utils.pattern_utils as pu
import utils.spacy_utils as su
import utils.tweet_keys as tk
from utils.id_freq_dict import IdFreqDict
from config.dict_loader import token_dict


class GSDPMMStreamIFDDynamic:
    """ Dynamic cluster number, stream, dynamic dictionary, with ifd """
    
    def __init__(self):
        print(self.__class__.__name__)
        self.alpha = self.beta = self.beta0 = None
        self.state = 0
        self.max_cluid = 0
        self.hold_batch_num = None
        self.twh_batches = list()
        self.cludict = {self.max_cluid: ClusterHolder(self.max_cluid)}
    
    def set_hyperparams(self, hold_batch_num, alpha, beta):
        self.hold_batch_num = hold_batch_num
        self.alpha = alpha
        self.beta = beta
    
    def input_batch(self, tw_batch):
        # Assume that the twarr has been processed by spacy
        tw_batch = self.pre_process_twarr(tw_batch)
        if len(self.twh_batches) < self.hold_batch_num:
            self.twh_batches.append(tw_batch)
            return None
        elif self.state == 0:
            self.state = 1
            self.twh_batches.append(tw_batch)
            current_twarr = au.merge_array(self.twh_batches)
            self.GSDPMM_twarr([], current_twarr, iter_num=20)
            return self.get_twid_cluid_batches(self.twh_batches)
        else:
            current_twarr = au.merge_array(self.twh_batches)
            self.GSDPMM_twarr(current_twarr, tw_batch, iter_num=3)
            self.twh_batches.append(tw_batch)
            oldest_twarr = self.twh_batches.pop(0)
            for twh in oldest_twarr:
                twh.update_cluster(None)
            self.check_empty_cluster()
            return self.get_twid_cluid_batches([tw_batch])
    
    def get_twarr(self):
        return [twh.tw for twh in au.merge_array(self.twh_batches)]
    
    @staticmethod
    def get_twid_cluid_batches(tw_batches):
        return [[(tw[tk.key_id], tw[tk.key_event_cluid]) for tw in batch] for batch in tw_batches]
    
    @staticmethod
    def pre_process_twarr(twarr):
        return [TweetHolder(tw) for tw in twarr]
    
    def filter_twarr_id(self, twarr):
        self_ids = set([tw[tk.key_id] for tw in au.merge_array(self.twh_batches)])
        for idx in range(len(twarr) - 1, -1, -1):
            if tk.key_id not in twarr[idx] or twarr[idx][tk.key_id] not in self_ids:
                twarr.pop(idx)
        return twarr
    
    def check_empty_cluster(self):
        for cluid in list(self.cludict.keys()):
            cluster = self.cludict[cluid]
            if cluster.twnum == 0:
                assert len(cluster.twhdict) == 0
                self.cludict.pop(cluid)
    
    def sample(self, twh, D, using_max=False, no_new_clu=False, cluid_range=None):
        alpha = self.alpha
        beta = self.beta
        beta0 = self.beta0
        cludict = self.cludict
        cluids = list()
        probs = list()
        # tw_word_freq = twh.valid_tokens.word_freq_enumerate(newest=False)
        tw_word_freq = twh.tokens.word_freq_enumerate(newest=False)
        if cluid_range is None:
            cluid_range = cludict.keys()
        for cluid in cluid_range:
            cluster = cludict[cluid]
            clu_tokens = cluster.tokens
            n_zk = clu_tokens.get_freq_sum() + beta0
            old_clu_prob = cluster.twnum / (D - 1 + alpha)
            prob_delta = 1.0
            ii = 0
            for word, freq in tw_word_freq:
                n_zwk = clu_tokens.freq_of_word(word) if clu_tokens.has_word(word) else 0
                if freq == 1:
                    prob_delta *= (n_zwk + beta) / (n_zk + ii)
                    ii += 1
                else:
                    for jj in range(freq):
                        prob_delta *= (n_zwk + beta + jj) / (n_zk + ii)
                        ii += 1
            cluids.append(cluid)
            probs.append(old_clu_prob * prob_delta)
        if not no_new_clu:
            ii = 0
            new_clu_prob = alpha / (D - 1 + alpha)
            prob_delta = 1.0
            for word, freq in tw_word_freq:
                if freq == 1:
                    prob_delta *= beta / (beta0 + ii)
                    ii += 1
                else:
                    for jj in range(freq):
                        prob_delta *= (beta + jj) / (beta0 + ii)
                        ii += 1
            cluids.append(self.max_cluid + 1)
            probs.append(new_clu_prob * prob_delta)
        
        if using_max:
            return cluids[np.argmax(probs)]
        else:
            return int(np.random.choice(a=cluids, p=np.array(probs) / np.sum(probs)))
    
    def GSDPMM_twarr(self, old_twharr, new_twharr, iter_num):
        cludict = self.cludict
        valid_dict = IdFreqDict()
        if len(old_twharr) > 0:
            for cluster in cludict.values():
                cluster.clear()
        D = len(old_twharr) + len(new_twharr)
        """ recalculate the valid dictionary """
        for twh in old_twharr + new_twharr:
            valid_dict.merge_freq_from(twh.tokens, newest=False)
        valid_dict.drop_words_by_condition(3)
        """ reallocate & parameter """
        for old_twh in old_twharr:
            if old_twh.get_cluid() not in cludict:
                continue
            old_twh.validate(valid_dict)
            old_cluster = old_twh.cluster
            old_twh.cluster = None
            old_twh.update_cluster(old_cluster)
        for new_twh in new_twharr:
            new_twh.validate(valid_dict)
            if len(old_twharr) > 0:
                new_cluid = self.sample(new_twh, D, using_max=True, no_new_clu=True)
            else:
                new_cluid = self.max_cluid
            new_twh.update_cluster(cludict[new_cluid])
        self.beta0 = self.beta * valid_dict.vocabulary_size()
        """ start iteration """
        for i in range(iter_num):
            # print('\r{}\r{}, clu num: {}'.format(' ' * 10, i, len(self.cludict)), end='')
            print('{}, clu num: {}'.format(i, len(self.cludict)))
            for twh in new_twharr:
                cluster = twh.cluster
                twh.update_cluster(None)
                if cluster.twnum == 0:
                    cludict.pop(cluster.cluid)
                cluid = self.sample(twh, D, using_max=(i == iter_num - 1))
                if cluid not in cludict:
                    self.max_cluid += 1
                    cludict[self.max_cluid] = ClusterHolder(self.max_cluid)
                twh.update_cluster(cludict[self.max_cluid])
        for twh in new_twharr:
            twh.update_cluid_into_tw()
        # """ verify """
        # print('total tw by clusters:{}'.format(sum([cluster.twnum for cluster in self.cludict.values()])))
        # print('cluster number:{}'.format(len(self.cludict.keys())))
        # print('clu twnum distrb:{}'.format([cluster.twnum for cluster in self.cludict.values()]))
    
    """ extra functions """
    def get_hyperparams_info(self):
        return '{}, alpha={:<5}, beta={:<5}'.format(self.__class__.__name__, self.alpha, self.beta)
    
    key2func = dict([
        ('twarr', lambda c: c.get_twarr()),
        ('vecarr', lambda c: c.get_pos_vecarr()),
        ('vector', lambda c: c.get_pos_mean_vector()),
    ])
    
    def cluid2info(self, func):
        return dict([(cluid, func(cluster)) for cluid, cluster in self.cludict.items()])
    
    def cluid2info_by_key(self, key):
        func = GSDPMMStreamIFDDynamic.key2func[key]
        return self.cluid2info(func)
    
    def cluster_mutual_similarity(self):
        cluid2vector = self.cluid2info_by_key('vector')
        cluid_arr = sorted(cluid2vector.keys())
        clu_num = len(cluid_arr)
        assert clu_num >= 2
        vecarr = [cluid2vector[cluid] for cluid in cluid_arr]
        sim_matrix = au.cosine_similarity(vecarr)
        pair_sim_arr = list()
        for i in range(0, clu_num - 1):
            for j in range(i + 1, clu_num):
                pair_sim_arr.append([cluid_arr[i], cluid_arr[j], float(sim_matrix[i][j])])
        return pair_sim_arr


class ClusterHolder:
    def __init__(self, cluid):
        self.cluid = cluid
        self.twhdict = dict()
        self.tokens = IdFreqDict()
        self.twnum = 0
    
    """ basic functions """
    def get_twharr(self): return list(self.twhdict.values())
    
    def get_twarr(self): return [twh.tw for twh in self.twhdict.values()]
    
    def get_lbarr(self): return [twh[tk.key_event_label] for twh in self.twhdict.values()]
    
    def clear(self):
        self.twhdict.clear()
        self.tokens.clear()
        self.twnum = 0
    
    def update_by_twh(self, twh, factor):
        twh_tokens = twh.valid_tokens
        twh_id = twh.id
        if factor > 0:
            self.tokens.merge_freq_from(twh_tokens, newest=False)
            self.twhdict[twh_id] = twh
            self.twnum += 1
        else:
            self.tokens.drop_freq_from(twh_tokens, newest=False)
            if twh_id in self.twhdict:
                self.twhdict.pop(twh_id)
            self.twnum -= 1
    
    def tansfer_twarr(self, cluster):
        for twh in self.get_twharr():
            twh.update_cluster(cluster)
    
    """ extra functions """
    def get_rep_label(self, rep_thres):
        lb_count = Counter(self.get_lbarr())
        max_label, max_lbnum = lb_count.most_common(1)[0]
        rep_label = -1 if max_lbnum < self.twnum * rep_thres else max_label
        return rep_label
    
    def extract_keywords(self):
        pos_keys = {su.pos_prop, su.pos_comm, su.pos_verb}
        self.ifds = self.keyifd, self.entifd = IdFreqDict(), IdFreqDict()
        for twh in self.twhdict.values():
            doc = twh.get(tk.key_spacy)
            for token in doc:
                word, pos = token.text.strip().lower(), token.pos_
                if pos in pos_keys and word not in pu.stop_words:
                    self.keyifd.count_word(word)
            for ent in doc.ents:
                if ent.label_ in su.LABEL_LOCATION:
                    self.entifd.count_word(ent.text.strip().lower())
    
    def similarity_vec_with(self, cluster):
        def ifd_sim_vec(ifd1, ifd2):
            v_size1, v_size2 = ifd1.vocabulary_size(), ifd2.vocabulary_size()
            freq_sum1, freq_sum2 = ifd1.get_freq_sum(), ifd2.get_freq_sum()
            common_words = set(ifd1.vocabulary()).intersection(set(ifd2.vocabulary()))
            comm_word_num = len(common_words)
            comm_freq_sum1 = sum([ifd1.freq_of_word(w) for w in common_words])
            comm_freq_sum2 = sum([ifd2.freq_of_word(w) for w in common_words])
            portion1 = freq_sum1 / comm_freq_sum1 if comm_freq_sum1 > 0 else 0
            portion2 = freq_sum2 / comm_freq_sum2 if comm_freq_sum2 > 0 else 0
            comm_portion1 = comm_word_num / v_size1 if v_size1 > 0 else 0
            comm_portion2 = comm_word_num / v_size2 if v_size2 > 0 else 0
            return [portion1, portion2, comm_portion1, comm_portion2]
        this_keyifd, this_entifd = self.ifds
        that_keyifd, that_entifd = cluster.ifds
        sim_vec_key = ifd_sim_vec(this_keyifd, that_keyifd)
        sim_vec_ent = ifd_sim_vec(this_entifd, that_entifd)
        sim_vec = np.concatenate([sim_vec_key, sim_vec_ent], axis=0)
        return sim_vec


class TweetHolder:
    def __init__(self, tw):
        self.tw = tw
        self.id = tw.get(tk.key_id)
        self.cluster = None
        self.tokens = IdFreqDict()
        self.valid_tokens = IdFreqDict()
        self.tokenize(token_dict())
    
    def __contains__(self, key): return key in self.tw
    
    def __getitem__(self, key): return self.get(key)
    
    def __setitem__(self, key, value): self.setdefault(key, value)
    
    def get(self, key): return self.tw.get(key, None)
    
    def setdefault(self, key, value): self.tw.setdefault(key, value)
    
    def get_cluid(self): return self.cluster.cluid
    
    def update_cluid_into_tw(self):
        self.tw[tk.key_event_cluid] = self.cluster.cluid if self.cluster is not None else None
    
    def tokenize(self, using_ifd):
        self.tokens = IdFreqDict()
        for token in self.tw[tk.key_spacy]:
            word = token.text.lower().strip()
            if pu.is_valid_keyword(word) and using_ifd.has_word(word):
                self.tokens.count_word(word)
    
    def validate(self, using_ifd):
        self.valid_tokens.clear()
        for word, freq in self.tokens.word_freq_enumerate(newest=False):
            if using_ifd.has_word(word):
                self.valid_tokens.count_word(word, freq)
    
    def update_cluster(self, cluster):
        if self.cluster is not None:
            self.cluster.update_by_twh(self, factor=-1)
        self.cluster = cluster
        if cluster is not None:
            cluster.update_by_twh(self, factor=1)
