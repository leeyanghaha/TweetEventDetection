import os
import shutil
from subprocess import Popen, PIPE

from config.Configure import getcfg
import utils.function_utils as fu
import utils.file_iterator as fi
import utils.multiprocess_utils as mu
import utils.tweet_keys as tk
import utils.timer_utils as tmu


autophrase_base = getcfg().autophrase_path
autophrase_output_base = os.path.join(autophrase_base, "OUTPUTS/")  # 保证任何autophrase的输出限制到output_base之内的某个角落
command = os.path.join(autophrase_base, "auto_phrase.sh")
fi.mkdir(autophrase_output_base)


def autophrase(input_text_file, output_path, commander, process_base, min_sup):
    p = Popen(commander, shell=True, bufsize=1, stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=process_base)
    p.stdin.flush()
    p.stdin.write((input_text_file + '\n').encode("utf8"))
    p.stdin.write((output_path + '\n').encode("utf8"))
    p.stdin.write((min_sup + '\n').encode("utf8"))
    p.stdin.flush()
    p.communicate()


def copy_from_base(process_base):
    if not os.path.exists(process_base):
        fi.mkdir(process_base)
        os.system("cp %s %s" % (command, process_base))
        os.system("cp %s %s" % (os.path.join(autophrase_base, 'phrasal_segmentation.sh'), process_base))
        os.system("cp -r %s %s" % (os.path.join(autophrase_base, 'bin'), process_base))
        os.system("cp -r %s %s" % (os.path.join(autophrase_base, 'data'), process_base))
        os.system("cp -r %s %s" % (os.path.join(autophrase_base, 'tools'), process_base))


def determine_min_sup(len_textarr):
    if len_textarr == 0:
        return 0
    default_sup = 10
    lookup = {(1, 30): 1, (30, 100): 2, (100, 1000): 3, (1000, 10000): 4, (10000, 100000): 5, }
    for (lower, upper), sup in lookup.items():
        if lower <= len_textarr < upper:
            return str(sup)
    return str(default_sup)


def autophrase_wrapper(process_code, textarr):
    # process_code用于辨识进程所占用的路径，textarr是一个文本list
    process_base = os.path.join(autophrase_output_base, str(process_code))
    commander = os.path.join(process_base, "auto_phrase.sh")
    input_text_file = os.path.join(process_base, "raw_train.txt")
    output_keyword_file = os.path.join(process_base, "AutoPhrase.txt")
    copy_from_base(process_base)
    # 将文本列表写入文件, 执行autophrase
    fu.write_lines(input_text_file, textarr)
    min_sup = determine_min_sup(len(textarr))
    autophrase(input_text_file, process_base, commander, process_base, min_sup)
    # 读取autophrase结果
    lines = fu.read_lines(output_keyword_file)
    conf_word_list = list()
    for line in lines:
        conf, word = line.split(maxsplit=1)
        conf_word_list.append((float(conf), word))
    shutil.rmtree(os.path.join(process_base, 'tmp'))
    return conf_word_list


def autophrase_multi(twarr_list, process_num):
    """ Returns a keyword list that has not been filtered yet """
    # twarr_list里每个元素都是一个twarr(list类型)，twarr的每个元素是一个推文(dict类型)
    def get_textarr(twarr):
        return [tw[tk.key_text] for tw in twarr]
    index = 0
    keywords_list = list()
    while index < len(twarr_list):
        twarr_batch = twarr_list[index: index + process_num]
        arg_list = [(idx, get_textarr(twarr)) for idx, twarr in enumerate(twarr_batch)]
        keywords_list_batch = mu.multi_process(autophrase_wrapper, arg_list)
        keywords_list.extend(keywords_list_batch)
        index += process_num
    return keywords_list


def autophrase_multi_top_results(twarr_list, process_num, max_word_num):
    keywords_list = autophrase_multi(twarr_list, process_num)
    return fileter_keyword_list(keywords_list, max_word_num)


def fileter_keyword_list(keywords_list, max_word_num):
    return [filter_keywords(keywords, max_word_num) for keywords in keywords_list]


def filter_keywords(keywords, max_word_num):
    return [word for idx, (conf, word) in enumerate(keywords) if word_filter_func(conf, word)][:max_word_num]


def word_filter_func(conf, word):
    return conf > 0.5 and len(word) > 2


if __name__ == '__main__':
    """ 文本数量小于30时关键词的质量已经相当低，应尽量使进入的文本数量大于一定阈值 """
    # __main__里面的内容保持不变，是最终的接口形式
    _keywords_list = fu.load_array('qwer')
    for keyword in _keywords_list:
        print(filter_keywords(keyword, 20), '\n')
    exit()
    
    base = "/home/nfs/cdong/tw/seeding/Terrorist/queried/positive/"
    _files = fi.listchildren(base, fi.TYPE_FILE, concat=True)
    _twarr_list = [fu.load_array(file) for file in _files]
    tmu.check_time()
    _keywords_list = autophrase_multi(_twarr_list, process_num=10)  # 主要验证这个输出结果是否正确以及是否有加速
    tmu.check_time()
    fu.dump_array('qwer', _keywords_list)
    _keywords_list = fu.load_array('qwer')
    print(len(_keywords_list))
    print([len(_keywords) for _keywords in _keywords_list])
    assert len(_twarr_list) == len(_keywords_list)
    for _idx, _keywords in enumerate(_keywords_list):
        # print('word num', len(_keywords), ', tw num', len(_twarr_list[idx]))
        if len(_keywords) < 20:
            print(len(_twarr_list[_idx]))
