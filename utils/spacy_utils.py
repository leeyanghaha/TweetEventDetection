import spacy
from collections import Counter


model = 'en_core_web_lg'
default_model_id = 'default'


def new_nlp(_model):
    try:
        return spacy.load(_model)
    except:
        print('load model error')
        return None


class NlpGetter:
    nlp_dict = {}
    
    def __call__(self, _model=model, _model_id=default_model_id):
        _model_name = 'model:{}, id:{}'.format(_model, _model_id)
        nlp_dict = NlpGetter.nlp_dict
        if _model_name not in nlp_dict:
            nlp_dict.setdefault(_model_name, new_nlp(_model))
        return nlp_dict.get(_model_name)


get_nlp = NlpGetter()


def text_nlp(text, nlp=None):
    if nlp is None:
        nlp = get_nlp()
    return nlp(text)


def textarr_nlp(textarr, nlp=None, n_threads=4):
    if nlp is None:
        nlp = get_nlp()
    return [doc for doc in nlp.pipe(textarr, n_threads=n_threads)]


# doc = su.text_nlp(get_text(tw), nlp)
# [(token.text, token.ent_type_, token.tag_, token.pos_, ) for token in doc]
# [ent.label_ for ent in doc.ents]


pos_prop = 'PROPN'
pos_comm = 'NOUN'
pos_verb = 'VERB'
pos_hstg = 'HSTG'
# key_ent = 'ENT'
# ent_glf = {'FAC', 'GPE', 'LOC'}
target_types = [pos_hstg, pos_prop, pos_comm, pos_hstg]


# class SpacyServicePool:
#     def __init__(self):
#         self.dae_pool = list()
#         # self.service_on = False
#
#     def start(self, pool_size, nlp_model):
#         # if self.service_on:
#         #     return
#         for i in range(pool_size):
#             daeprocess = SpacyDaemonProcess(_nlp_service)
#             daeprocess.start(i)
#             daeprocess.set_model(nlp_model)
#             self.dae_pool.append(daeprocess)
#         # for daeprocess in self.dae_pool:
#         #     daeprocess.wait_for_daemon()
#         # self.service_on = True
#
#     def execute_nlp_multiple(self, textarr):
#         import sys
#
#         textarr_blocks = fu.split_multi_format(textarr, len(self.dae_pool))
#         res = []
#         for block_idx in range(len(textarr_blocks)):
#             dae = self.dae_pool[block_idx]
#             textarr = textarr_blocks[block_idx]
#             dae.set_text_arr(textarr)
#         for block_idx in range(len(textarr_blocks)):
#             dae = self.dae_pool[block_idx]
#             output = dae.get_nlp_arr()
#             print('receiving', block_idx, sys.getsizeof(output))
#             res.extend(output)
#         return res
#
#
# class SpacyDaemonProcess:
#     C_SETMODEL, C_NLPTEXT, C_END, R_SUCCESS = 'setmodel', 'nlp', 'end', 'success'
#
#     def __init__(self, func):
#         self.process = None
#         self.func = func
#         self.inq = mp.Queue()
#         self.outq = mp.Queue()
#
#     def start(self, pidx):
#         self.process = mp.Process(target=self.func, args=(self.inq, self.outq, pidx))
#         self.process.daemon = True
#         self.process.start()
#
#     def wait_for_daemon(self):
#         if self.outq.get() == SpacyDaemonProcess.R_SUCCESS:
#             return
#         else:
#             raise ValueError('Service failed.')
#
#     def end(self):
#         self.inq.put(SpacyDaemonProcess.C_END)
#
#     def set_model(self, _model):
#         self.inq.put(SpacyDaemonProcess.C_SETMODEL)
#         self.inq.put(_model)
#
#     def set_text_arr(self, textarr):
#         self.inq.put(SpacyDaemonProcess.C_NLPTEXT)
#         self.inq.put(textarr)
#
#     def get_nlp_arr(self):
#         return self.outq.get()
#
#
# def _nlp_service(inq, outq, pidx=0):
#     _pidx = pidx
#     _nlp = None
#     while True:
#         command = inq.get()
#         if command == SpacyDaemonProcess.C_SETMODEL:
#             _model = inq.get()
#             _nlp = new_nlp(_model)
#             # outq.put(SpacyDaemonProcess.R_SUCCESS)
#         elif command == SpacyDaemonProcess.C_NLPTEXT:
#             _textarr = inq.get()
#             _docarr = [_nlp(_text) for _text in _textarr]
#             outq.put(_docarr)
#         elif command == SpacyDaemonProcess.C_END:
#             del _nlp
#             # outq.put(SpacyDaemonProcess.R_SUCCESS)
#             return
#
#
# ssp = SpacyServicePool()
#
#
# def start_service(pool_size=8, nlp_model=model):
#     ssp.start(pool_size=pool_size, nlp_model=nlp_model)
#
#
# def execute_nlp_multiple(textarr):
#     return ssp.execute_nlp_multiple(textarr)


# def doc_ents(doc):
#     return [(ent.text, ent.label_, ent.root.tag_) for ent in doc.ents]
# def twarr_ner_(twarr, from_key=tk.key_text, to_key=tk.key_spacy):
#     for tw in twarr:
#         ents = en_nlp(tw[from_key]).ents
#         tw[to_key] = ((ent.text, ent.root.tag_, ent.label_) for ent in ents)