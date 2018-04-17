import utils.function_utils as fu
import utils.tweet_keys as tk
import utils.file_iterator as fi
import re


class Level:
    def __init__(self):
        self.injured_word = {'seriously', 'wounded', 'injured', 'critical', 'hurt', 'injuring', 'casualties',
                             'moderately', 'wounding', 'wounds', 'civilians', 'wound', 'missing', 'least',
                             'people'}
        self.death_word = {'kills', 'killing', 'kill', 'dead', 'killed', 'martyrs','die'}
    
    def get_single_tweet_injured_death(self, tweet):
        word_list = tweet.lower().split()
        injured_number = death_number = 0
        for i in range(1, len(word_list) - 1):
            if word_list[i] in self.injured_word:
                try:
                    injured_number = self.spoken_word_to_number(word_list[i - 1])
                except AssertionError:
                    try:
                        injured_number = self.spoken_word_to_number(word_list[i + 1])
                    except AssertionError:
                        injured_number = 0
            if word_list[i] in self.death_word:
                try:
                    death_number = self.spoken_word_to_number(word_list[i - 1])
                except AssertionError:
                    try:
                        death_number = self.spoken_word_to_number(word_list[i + 1])
                    except AssertionError:
                        death_number = 0
            death_number_match = re.match('\d*\d$', str(death_number))
            death_number = int(death_number_match.group()) if death_number_match else 0
            injured_number_match = re.match('\d*\d$', str(injured_number))
            injured_number = int(injured_number_match.group()) if death_number_match else 0
            if injured_number == death_number:
                death_number = 0
        return {'death': death_number, 'injured': injured_number}
    
    def get_all(self, twarr):
        injured_dict = dict()
        death_dict = dict()
        for tweet in twarr:
            text = tweet[tk.key_text]
            single_tweet_injured_death = self.get_single_tweet_injured_death(text)
            injured_num = single_tweet_injured_death['injured']
            death_num = single_tweet_injured_death['death']
            if injured_num not in injured_dict:
                injured_dict.update({injured_num: 0})
            else:
                injured_dict[injured_num] += 1
            if death_num not in death_dict:
                death_dict.update({death_num: 0})
            else:
                death_dict[death_num] += 1
        if 0 in death_dict:
            del death_dict[0]
        if 0 in injured_dict:
            del injured_dict[0]
        injured_number = death_number = 0
        if death_dict:
            death_number = max(death_dict.items(), key=lambda x: x[1])[0]
        if injured_dict:
            injured_number = max(injured_dict.items(), key=lambda x: x[1])[0]
        return {'injured': injured_number, 'death': death_number}
    
    def get_level(self, twarr):
        ret = self.get_all(twarr)
        injured_num = ret['injured']
        death_num = ret['death']
        if injured_num == death_num:
            count = death_num
        else:
            count = death_num + injured_num
        if count < 30:
            level = '一般事件'
        elif 30 < count < 100:
            level = '较大事件'
        elif 100 < count < 300:
            level = '重大事件'
        else:
            level = '特别重大事件'
        if level == '':
            level = 'Cannot calculate hot_and_level'
        return level
    
    def spoken_word_to_number(self, n):
        number = re.match('\d*\d', n)
        if number:
            return number.group()
        _known = {
            'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
            'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12,
            'thirteen': 13, 'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17,
            'eighteen': 18, 'nineteen': 19, 'twenty': 20, 'thirty': 30, 'forty': 40,
            'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90
        }
        n = n.lower().strip()
        if n in _known:
            return _known[n]
        else:
            inputWordArr = re.split('[ -]', n)
        assert len(inputWordArr) > 1  # all single words are known
        # Check the pathological case where hundred is at the end or thousand is at end
        if inputWordArr[-1] == 'hundred':
            inputWordArr.append('zero')
            inputWordArr.append('zero')
        if inputWordArr[-1] == 'thousand':
            inputWordArr.append('zero')
            inputWordArr.append('zero')
            inputWordArr.append('zero')
        if inputWordArr[0] == 'hundred':
            inputWordArr.insert(0, 'one')
        if inputWordArr[0] == 'thousand':
            inputWordArr.insert(0, 'one')
        inputWordArr = [word for word in inputWordArr if word not in ['and', 'minus', 'negative']]
        currentPosition = 'unit'
        prevPosition = None
        output = 0
        for word in reversed(inputWordArr):
            if currentPosition == 'unit':
                number = _known[word]
                output += number
                if number > 9:
                    currentPosition = 'hundred'
                else:
                    currentPosition = 'ten'
            elif currentPosition == 'ten':
                if word != 'hundred':
                    number = _known[word]
                    if number < 10:
                        output += number * 10
                    else:
                        output += number
                currentPosition = 'hundred'
            elif currentPosition == 'hundred':
                if word not in ['hundred', 'thousand']:
                    number = _known[word]
                    output += number * 100
                    currentPosition = 'thousand'
                elif word == 'thousand':
                    currentPosition = 'thousand'
                else:
                    currentPosition = 'hundred'
            elif currentPosition == 'thousand':
                assert word != 'hundred'
                if word != 'thousand':
                    number = _known[word]
                    output += number * 1000
            else:
                assert "Can't be here" is None
        return output


class AttackLevel(Level):
    def __int__(self):
        Level.__init__(self)
