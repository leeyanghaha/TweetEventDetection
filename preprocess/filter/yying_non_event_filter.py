import os
import re
import sys
import pickle
import datetime
import traceback

import numpy as np
import pandas as pd
from sklearn import metrics

from config.configure import getcfg
from preprocess.filter.filter_utils import get_all_substrings
from preprocess.filter.pos_tag_process import count_sentiment

import utils.array_utils as au
import utils.function_utils as fu
import utils.file_iterator as fi
import utils.pattern_utils as pu
import utils.tweet_keys as tk
import utils.timer_utils as tmu


sys.path.append(os.path.abspath(os.path.dirname(__file__)))

chat_filter_file = getcfg().chat_filter_file
is_noise_dict_file = getcfg().is_noise_dict_file
clf_model_file = getcfg().clf_model_file
black_list_file = getcfg().black_list_file


class UseGSDMM:
    def __init__(self):
        try:
            with open(chat_filter_file, 'rb') as f:
                self.c = pickle.load(f)
            with open(is_noise_dict_file, 'rb') as f:
                self.is_noise_dict = set(pickle.load(f))
        except:
            print('load error')
            traceback.print_exc()

    def get_GSDMM_Feature(self, json):
        """ is tw a chat or not """
        if tk.key_orgntext in json:
            json[tk.key_text] = pu.text_normalization(json[tk.key_orgntext])
        else:
            text = json[tk.key_text]
            json[tk.key_orgntext] = text
            json[tk.key_text] = pu.text_normalization(text)
        topic_num = self.c.sample_cluster(json)
        if topic_num in self.is_noise_dict:
            return 1
        return 0


class EffectCheck:
    def __init__(self, spam_word_file=black_list_file, classify_model_file=clf_model_file):
        self.gsdmm = UseGSDMM()
        if spam_word_file is not None and classify_model_file is not None:
            with open(spam_word_file, 'r') as fp:
                self.spam_words = set([line.strip() for line in fp.readlines()])
            with open(classify_model_file, 'rb') as f:
                self.clf = pickle.load(f)
    
    def get_features(self, json):
        user = json[tk.key_user]
        if tk.key_description in user and user[tk.key_description] is not None:
            l_profile_description = len(user[tk.key_description])
        else:
            l_profile_description = 0
        FI = user[tk.key_friends_count]
        FE = user[tk.key_followers_count]
        num_tweet_posted = user[tk.key_statuses_count]
        
        tw_time = json[tk.key_created_at]
        user_born_time = json[tk.key_user][tk.key_created_at]
        # TODO 有些推文时间字段有误，需要判断处理，比如缺了分秒信息
        tw_d = datetime.datetime.strptime(tw_time, '%a %b %d %H:%M:%S %z %Y')
        user_d = datetime.datetime.strptime(user_born_time, '%a %b %d %H:%M:%S %z %Y')
        time_delta = tw_d - user_d
        AU = time_delta.seconds / 60.0 + time_delta.days * 24
        FE_FI_ratio = 0
        if FI != 0:
            FE_FI_ratio = FE / float(FI)
        reputation = 0
        if (FI + FE) != 0:
            reputation = FE / float(FI + FE)
        
        following_rate = FI / float(AU)
        tweets_per_day = num_tweet_posted / (AU / 24)
        tweets_per_week = num_tweet_posted / (AU / (24 * 7))
        
        user_features = [l_profile_description, FI, FE, num_tweet_posted, AU, FE_FI_ratio,
                         reputation, following_rate, tweets_per_day, tweets_per_week]
        """ content features """
        # if tk.key_orgntext not in json:
        #     json[tk.key_orgntext] = json[tk.key_text]
        #     json[tk.key_text] = pu.text_normalization(json[tk.key_orgntext])
        orgn = json[tk.key_orgntext]
        text = json[tk.key_text]
        words = text.split()
        num_words = len(words)
        num_charater = len(text)
        num_white_space = len(re.findall(r'(\s)', text))
        num_capitalization_word = len(re.findall(r'(\b[A-Z]([a-z])*\b)', text))
        num_capital_per_word = num_capitalization_word / num_words
        
        max_word_length = 0
        mean_word_length = 0
        # assert (len(words) > 0)
        for word in words:
            if len(word) > max_word_length:
                max_word_length = len(word)
                mean_word_length += len(word)
        mean_word_length /= len(words)
        num_exclamation_marks = orgn.count('!')
        num_question_marks = orgn.count('?')
        num_urls = len(json['entities']['urls'])
        num_urls_per_word = num_urls / num_words
        num_hashtags = len(json['entities']['hashtags'])
        num_hashtags_per_word = num_hashtags / num_words
        num_mentions = len(json['entities']['user_mentions'])
        num_mentions_per_word = num_mentions / num_words
        
        substrings = get_all_substrings(text)
        num_spam_words = 0
        for sub in substrings:
            if sub in self.spam_words:
                num_spam_words += 1
        num_spam_words_per_word = num_spam_words / num_words
        content_features = [num_words, num_charater, num_white_space, num_capitalization_word,
                            num_capital_per_word, max_word_length, mean_word_length,
                            num_exclamation_marks, num_question_marks, num_urls, num_urls_per_word,
                            num_hashtags, num_hashtags_per_word, num_mentions,
                            num_mentions_per_word, num_spam_words, num_spam_words_per_word]
        sentiment_frature = count_sentiment(text)
        chat_feature = self.gsdmm.get_GSDMM_Feature(json)
        total_features = list()
        total_features.extend(user_features)
        total_features.extend(content_features)
        total_features.append(sentiment_frature)
        total_features.append(chat_feature)
        return total_features
    
    # def predict(self, twarr, threshold):
    #     probarr = self.predict_proba(twarr)
    #     predarr = [1 if prob > threshold else 0 for prob in probarr]
    #     return predarr
    
    def predict_proba(self, twarr):
        featurearr, ignore_idx = list(), list()
        for idx, tw in enumerate(twarr):
            try:
                featurearr.append(self.get_features(tw))
            except Exception as e:
                ignore_idx.append(idx)
        probarr = list(self.clf.predict_proba(featurearr)[:, 1])
        for idx in ignore_idx:
            probarr.insert(idx, 0)
        for idx in ignore_idx:
            print('invalid tw with text:{} ,label:{}'.format(twarr[idx].get(tk.key_text), probarr[idx]))
        return probarr
    
    def filter(self, twarr, threshold):
        probarr = self.predict_proba(twarr)
        filter_twarr = [tw for idx, tw in enumerate(twarr) if probarr[idx] >= threshold]
        return filter_twarr
    
    def get_filter_res(self, twarr):
        data = [self.get_features(tw) for tw in twarr]
        predict = self.clf.predict(data)
        table = pd.DataFrame(index={"data"}, columns={'保留', '被过滤'}, data=0)
        for i in range(len(predict)):
            if predict[i] == 1:
                table.loc["data", '保留'] += 1
            else:
                table.loc["data", '被过滤'] += 1
        print(table)
        print('总数：', len(predict), '过滤比例：', table.loc["data"]['被过滤'] / len(predict))


def perfomance_analysis():
    labal, proba = fu.load_array('label_proba')
    print(len(labal), len(proba))
    au.precision_recall_threshold(labal, proba)


if __name__ == '__main__':
    my_filter = EffectCheck()
    
    sub_files = fi.listchildren('/home/nfs/cdong/tw/origin/', fi.TYPE_FILE, concat=True)[18:19]
    twarr = au.merge_array([fu.load_array(file) for file in sub_files])
    print(len(twarr))
    tmu.check_time(print_func=None)
    for idx, tw in enumerate(twarr[14000:15000]):
        if (idx + 1) % 1000 == 0:
            print(idx)
        try:
            my_filter.get_features(tw)
        except:
            # print(tw[tk.key_text])
            # print(tw[tk.key_orgntext])
            print('-', pu.text_normalization(tw[tk.key_orgntext]))
    tmu.check_time(print_func=lambda dt: print('pos filter time elapsed {}s'.format(dt)))
    
    exit()
    
    pos_base = '/home/nfs/cdong/tw/seeding/Terrorist/queried/event_corpus/'
    sub_files = fi.listchildren(pos_base, fi.TYPE_FILE, 'txt$', concat=True)
    pos_twarr = au.merge_array([fu.load_array(file) for file in sub_files])
    print(len(pos_twarr))
    tmu.check_time(print_func=None)
    pos_proba = my_filter.predict_proba(pos_twarr)
    tmu.check_time(print_func=lambda dt: print('pos filter time elapsed {}s'.format(dt)))
    
    neg_files = [
        '/home/nfs/yying/data/crawlTwitter/Crawler1/test.json',
        '/home/nfs/yying/data/crawlTwitter/Crawler2/crawl2.json',
        '/home/nfs/yying/data/crawlTwitter/Crawler3/crawl3.json',
        '/home/nfs/cdong/tw/seeding/Terrorist/queried/Terrorist_counter.sum'
    ]
    neg_proba_list = list()
    for neg_file in neg_files:
        neg_twarr = fu.load_array(neg_file)
        print(len(neg_twarr))
        tmu.check_time(print_func=None)
        neg_proba = my_filter.predict_proba(neg_twarr)
        tmu.check_time(print_func=lambda dt: print('neg filter time elapsed {}s'.format(dt)))
        neg_proba_list.append(neg_proba)
    neg_probas = list(np.concatenate(neg_proba_list))
    
    labal = [1 for _ in pos_proba] + [0 for _ in neg_probas]
    proba = pos_proba + neg_probas
    fu.dump_array('label_proba', [labal, proba])
    perfomance_analysis()
    
    # print(len(my_filter.filter(data)))
