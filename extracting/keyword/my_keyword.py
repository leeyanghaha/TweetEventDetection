from collections import Counter

import utils.function_utils as fu
import utils.timer_utils as tmu
import utils.pattern_utils as pu
import utils.tweet_keys as tk


long_word2seg = dict()


def segment_long_word(word):
    if word not in long_word2seg:
        long_word2seg[word] = pu.segment(word)
    return long_word2seg[word]


def valid_tokens_of_text(text):
    pre_tokens = pu.tokenize(r'[\_\w\-]{2,}', text)
    seg_tokens = list()
    for token in pre_tokens:
        if len(token) > 16:
            seg_tokens.extend(segment_long_word(token))
        else:
            seg_tokens.append(token)
    return seg_tokens


def construct_n_grams(tokens, n):
    if len(tokens) < n:
        return list()
    grams = list()
    if n <= 1:
        for token in tokens:
            if pu.has_azAZ(token) and not pu.is_stop_word(token):
                grams.append(token)
    else:
        for i in range(len(tokens) - n + 1):
            words = tokens[i: i + n]
            phrase = ' '.join(words)
            grams.append(phrase)
    return grams


def get_keywords(textarr):
    k_list, k_counter = 'k_list', 'k_counter'
    n2grams = dict([(i, {k_list: list(), k_counter: None}) for i in range(1, 5)])
    tokens_list = list()
    for text in textarr:
        text = text.lower().strip()
        tokens = valid_tokens_of_text(text)
        tokens_list.append(tokens)
    for n in n2grams.keys():
        for tokens in tokens_list:
            n2grams[n][k_list].extend(construct_n_grams(tokens, n))
        n2grams[n][k_counter] = Counter(n2grams[n][k_list])
    def counter2words(counter):
        return [word for word, freq in counter.most_common(5)]
    print(len(twarr))
    for n in sorted(n2grams.keys()):
        print(len(n2grams[n][k_list]), counter2words(n2grams[n][k_counter]))
    return [counter2words(n2grams[n][k_counter]) for n in sorted(n2grams.keys())]


if __name__ == "__main__":
    file = "/home/nfs/cdong/tw/seeding/Terrorist/queried/event_corpus/2016-03-26_suicide-bomb_Lahore.txt"
    twarr = fu.load_array(file)
    tmu.check_time()
    # for i in range(200):
    get_keywords([tw[tk.key_text] for tw in twarr])
    tmu.check_time()
