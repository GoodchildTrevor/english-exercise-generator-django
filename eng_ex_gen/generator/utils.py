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

# Модели загружаются при старте один раз и шарятся между воркерами через --preload
print("Loading NLP models...")
model = api.load("glove-wiki-gigaword-100")
nlp = spacy.load('en_core_web_sm')
print("NLP models loaded.")

dependencies = ['predet', 'ROOT', 'amod', 'nsubj', 'pobj', 'dobj', 'ccomp']
dependencies_full = ['subject', 'predicate', 'adjectival modifier', 'nominal subject',
                     'object of a preposition', 'direct object', 'clausal complement']
main_pos = ['NOUN', 'VERB', 'ADV', 'ADJ']
main_pos_names = ['noun', 'verb', 'adverb', 'adjective']

types = ['select_sent', 'select_pos', 'select_word', 'verb_form', 'missing_word', 'noun_phrases']
description = ['Какое предложение верно?', 'Определите часть речи', 'Выберите слово',
               'Выберите верную форму глагола', 'Какое слово пропущено?', 'Определите часть предложения']


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
                f'В вашем тексте не должно быть больше 30 предложений. '
                f'Сейчас их {len(proc_sentences)}, введите текст снова.'
            )
        return proc_sentences

    def language_checking(self, raw_sentences):
        has_english = any(self.check_language(sentence) for sentence in raw_sentences)
        if not has_english:
            raise NoEnglishSentenceError(
                'Ваш текст должен содержать хотя бы одно предложение на английском языке.'
            )
        return has_english


class Tasks:

    def __init__(self, processing):
        self.processing = processing

    def random_words(self, original_word):
        similar_words = model.similar_by_word(original_word)
        selected_words = [word[0] for word in similar_words[:5] if word[0][0].isalpha()]
        selected_words = random.sample(selected_words, 3)
        selected_words.append(original_word)
        random.shuffle(selected_words)
        return selected_words

    def random_sentence(self, input_sentence):
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
        candidates = [w for w in words if w in model and len(w) > 3]
        if not candidates:
            return random.choice(words)
        return random.choice(candidates)

    def replace_random_word(self, r_word, sentence):
        return sentence.replace(f' {r_word}', ' _____ ')

    def make_tasks(self, raw_sentences, difficulty):
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
