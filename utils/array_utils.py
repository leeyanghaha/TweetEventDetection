import numpy as np
from collections import Counter
from sklearn import metrics


def random_array_items(array, item_num, keep_order=True):
    """
    Get random items from array.
    :param array: From which items are extracted.
    :param item_num: Number of items to be extracted.
    :param keep_order: If remains the relative order within array in the result.
    :return:
    """
    array_len = len(array)
    item_num = array_len if item_num >= array_len else item_num
    indexes = np.random.choice(array_len, item_num, replace=False)
    indexes = sorted(indexes) if keep_order else indexes
    return [array[i] for i in indexes]


def array_partition(array, partition_arr=(1, 1, 1), random=True, ordered=False):
    indexes = index_partition(array, partition_arr, random)
    return [[array[j] for j in indexes[i]] for i in range(len(indexes))]


def index_partition(array, partition_arr=(1, 1, 1), random=True, ordered=False):
    item_num = len(array)
    indexes = np.array([i for i in range(item_num)])
    indexes = shuffle(indexes) if random else indexes
    normed_portion = np.array(partition_arr) / np.sum(partition_arr)
    sum_idx = [0]
    sum_normed_por = [0]
    for portion in normed_portion:
        sum_normed_por.append(sum_normed_por[-1] + portion)
        sum_idx.append(int(sum_normed_por[-1] * item_num))
    sum_idx[-1] = item_num
    return [indexes[sum_idx[i]: sum_idx[i + 1]] for i in range(len(partition_arr))]


def shuffle(array, new_arr=False):
    array = array[:] if new_arr else array
    np.random.shuffle(array)
    return array


def roc_auc(labels_true, scores):
    return metrics.roc_auc_score(labels_true, scores)


def score(labels_true, labels_pred, score_type):
    if score_type == 'roc':
        return metrics.roc_auc_score(labels_true, labels_pred)
    elif score_type == 'nmi':
        return metrics.normalized_mutual_info_score(labels_true, labels_pred)
    elif score_type == 'homo':
        return metrics.homogeneity_score(labels_true, labels_pred)
    elif score_type == 'cmplt':
        return metrics.completeness_score(labels_true, labels_pred)


def group_array_by_condition(array, item_key):
    dictionary = dict()
    for item in array:
        item_key = item_key(item)
        if item_key not in dictionary:
            dictionary[item_key] = [item]
        else:
            dictionary[item_key].append(item)
    return [dictionary[key] for key in sorted(dictionary.keys())]


def sample_index_by_array_value(array):
    return np.random.choice(a=[i for i in range(len(array))], p=np.array(array) / np.sum(array))