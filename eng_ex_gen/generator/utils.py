from sentence_splitter import SentenceSplitter
from langdetect import detect
import gensim.downloader as api
import pandas as pd
import numpy as np
import re
import random
import spacy
import en_core_web_sm
import pyinflect

splitter = SentenceSplitter(language='en')

_model = None
_nlp = None


def get_model():
    global _model
    if _model is None:
        _model = api.load("glove-wiki-gigaword-100")
    return _model


def get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load('en_core_web_sm')
    return _nlp


dependencies = ['predet', 'ROOT', 'amod', 'nsubj', 'pobj', 'dobj', 'ccomp']
dependencies_full = ['subject', 'predicate', 'adjectival modifier', 'nominal subject',
                     'object of a preposition', 'direct object', 'clausal complement']
main_pos = ['NOUN', 'VERB', 'ADV', 'ADJ']
main_pos_names = ['noun', 'verb', 'adverb', 'adjective']

types = ['select_sent', 'select_pos', 'select_word', 'verb_form', 'missing_word', 'noun_phrases']
description = ['\u041a\u0430\u043a\u043e\u0435 \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u0435 \u0432\u0435\u0440\u043d\u043e?', '\u041e\u043f\u0440\u0435\u0434\u0435\u043b\u0438\u0442\u0435 \u0447\u0430\u0441\u0442\u044c \u0440\u0435\u0447\u0438', '\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0441\u043b\u043e\u0432\u043e',
               '\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0432\u0435\u0440\u043d\u0443\u044e \u0444\u043e\u0440\u043c\u0443 \u0433\u043b\u0430\u0433\u043e\u043b\u0430', '\u041a\u0430\u043a\u043e\u0435 \u0441\u043b\u043e\u0432\u043e \u043f\u0440\u043e\u043f\u0443\u0449\u0435\u043d\u043e?', '\u041e\u043f\u0440\u0435\u0434\u0435\u043b\u0438\u0442\u0435 \u0447\u0430\u0441\u0442\u044c \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u044f']


class TooManySentencesError(Exception):
    pass


class NoEnglishSentenceError(Exception):
    pass


class Processing:

    @staticmethod
    def check_language(sentence):
        try:
            if detect(sentence) == 'en':
                return True
        except Exception:
            return False

    def process_text(self, raw_text):
        proc_sentences = splitter.split(text=raw_text)
        if len(proc_sentences) > 30:
            raise TooManySentencesError(
                f'\u0412 \u0432\u0430\u0448\u0435\u043c \u0442\u0435\u043a\u0441\u0442\u0435 \u043d\u0435 \u0434\u043e\u043b\u0436\u043d\u043e \u0431\u044b\u0442\u044c \u0431\u043e\u043b\u044c\u0448\u0435 30 \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u0439. '
                f'\u0421\u0435\u0439\u0447\u0430\u0441 \u0438\u0445 {len(proc_sentences)}, \u0432\u0432\u0435\u0434\u0438\u0442\u0435 \u0442\u0435\u043a\u0441\u0442 \u0441\u043d\u043e\u0432\u0430.'
            )
        return proc_sentences

    def language_checking(self, raw_sentences):
        has_english = any(self.check_language(sentence) for sentence in raw_sentences)
        if not has_english:
            raise NoEnglishSentenceError(
                '\u0412\u0430\u0448 \u0442\u0435\u043a\u0441\u0442 \u0434\u043e\u043b\u0436\u0435\u043d \u0441\u043e\u0434\u0435\u0440\u0436\u0430\u0442\u044c \u0445\u043e\u0442\u044f \u0431\u044b \u043e\u0434\u043d\u043e \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u0435 \u043d\u0430 \u0430\u043d\u0433\u043b\u0438\u0439\u0441\u043a\u043e\u043c \u044f\u0437\u044b\u043a\u0435.'
            )
        return has_english


class Tasks:

    def __init__(self, processing):
        self.processing = processing

    def random_words(self, original_word):
        model = get_model()
        similar_words = model.similar_by_word(original_word)
        selected_words = [word[0] for word in similar_words[:5] if word[0][0].isalpha()]
        selected_words = random.sample(selected_words, 3)
        selected_words.append(original_word)
        random.shuffle(selected_words)
        return selected_words

    def random_sentence(self, input_sentence):
        model = get_model()
        similar_sentences = [input_sentence]
        for _ in range(3):
            similar_sentence = ''
            for token in input_sentence:
                if token.text in model.key_to_index:
                    if token.pos_ in main_pos:
                        sim_words = model.similar_by_word(token.text)
                        similar_sentence += random.choice(sim_words[:5])[0] + token.whitespace_
                    else:
                        similar_sentence += token.text + token.whitespace_
                else:
                    similar_sentence += token.text + token.whitespace_
            similar_sentence = re.sub(r'\s*,', ',', similar_sentence)
            similar_sentences.append(similar_sentence)
        random.shuffle(similar_sentences)
        return similar_sentences

    def deps(self, input_sentence):
        tokens_in_dependencies = []
        words_in_dependencies = []

        for token in input_sentence:
            if token.dep_ in dependencies:
                if token.text not in words_in_dependencies:
                    words_in_dependencies.append(token.text)
                    tokens_in_dependencies.append(token.dep_)

        random_wrd_cnstr = self.define_random_word(words_in_dependencies)
        random_dep = tokens_in_dependencies[words_in_dependencies.index(random_wrd_cnstr)]
        random_right_dep = dependencies_full[dependencies.index(random_dep)]
        options = random.sample([dep for dep in dependencies_full if dep != random_right_dep], 3)
        return random_wrd_cnstr, random_right_dep, options

    def define_random_word(self, words, max_attempts=50):
        model = get_model()
        candidates = [w for w in words if w in model and len(w) > 3]
        if not candidates:
            return random.choice(words)
        return random.choice(candidates)

    def replace_random_word(self, r_word, sentence):
        return sentence.replace(f' {r_word}', ' _____ ')

    def make_tasks(self, raw_sentences, difficulty):
        nlp = get_nlp()
        model = get_model()
        level = int(difficulty)
        df = pd.DataFrame(raw_sentences, columns=['sentence'])
        df = df[df['sentence'].str.strip() != ''].reset_index()
        df['type'] = np.nan
        df['description'] = np.nan
        df['options'] = np.nan
        df['answer'] = np.nan

        for index, row in df.iterrows():
            list_of_words = []
            doc = nlp(str(row['sentence']))
            if len(doc) > 7 and Processing.check_language(row['sentence']):
                if level == 1:
                    task_type = random.randint(0, 2) if len(doc) < 20 else random.randint(1, 2)
                elif level == 2:
                    task_type = random.choice([1, 2, 2, 2, 4])
                else:
                    task_type = random.choice([2, 4, 5])

                filtered_words = [token.text for token in doc if token.pos_ in main_pos]
                random_word = self.define_random_word(filtered_words)
                token = nlp(random_word)[0]

                if task_type == 1:
                    number_pos = main_pos.index(token.pos_)
                    df.loc[index, 'sentence'] = df.loc[index, 'sentence'].replace(str(random_word), f' [{random_word}] ')
                    df.loc[index, 'type'] = types[task_type]
                    df.loc[index, 'description'] = description[task_type]
                    df.loc[index, 'options'] = '//'.join(main_pos_names)
                    df.loc[index, 'answer'] = main_pos_names[number_pos]

                if task_type == 2:
                    if token.pos_ == 'VERB':
                        list_of_words.extend([
                            token._.inflect('VBP'), token._.inflect('VBZ'),
                            token._.inflect('VBG'), token._.inflect('VBD')
                        ])
                        df.loc[index, 'sentence'] = self.replace_random_word(random_word, row['sentence'])
                        df.loc[index, 'type'] = types[task_type + 1]
                        df.loc[index, 'description'] = description[task_type + 1]
                        df.loc[index, 'options'] = '//'.join(str(w) for w in list_of_words)
                        df.loc[index, 'answer'] = token._.inflect(token.tag_)
                    else:
                        list_of_words = self.random_words(random_word)
                        df.loc[index, 'sentence'] = self.replace_random_word(random_word, row['sentence'])
                        df.loc[index, 'type'] = types[task_type]
                        df.loc[index, 'description'] = description[task_type]
                        df.loc[index, 'options'] = '//'.join(list_of_words)
                        df.loc[index, 'answer'] = random_word

                if task_type == 0:
                    sentences = self.random_sentence(doc)
                    df.loc[index, 'sentence'] = '__________'
                    df.loc[index, 'type'] = types[task_type]
                    df.loc[index, 'description'] = description[task_type]
                    df.loc[index, 'options'] = '//'.join(str(s) for s in sentences)
                    df.loc[index, 'answer'] = row['sentence']

                if task_type == 4:
                    random_word = self.define_random_word(filtered_words)
                    df.loc[index, 'sentence'] = self.replace_random_word(random_word, row['sentence'])
                    df.loc[index, 'type'] = types[task_type]
                    df.loc[index, 'description'] = description[task_type]
                    df.loc[index, 'options'] = np.nan
                    df.loc[index, 'answer'] = random_word

                if task_type == 5:
                    wrd_cnstr, right_dep, other_deps = self.deps(doc)
                    other_deps.append(right_dep)
                    random.shuffle(other_deps)
                    df.loc[index, 'sentence'] = df.loc[index, 'sentence'].replace(str(wrd_cnstr), f' [{wrd_cnstr}] ')
                    df.loc[index, 'type'] = types[task_type]
                    df.loc[index, 'description'] = description[task_type]
                    df.loc[index, 'options'] = '//'.join(other_deps)
                    df.loc[index, 'answer'] = right_dep

        return df
