from django.shortcuts import render
from django.http import JsonResponse
from django import forms

from generator.models import Sentences
from generator.utils import Processing, Tasks, TooManySentencesError, NoEnglishSentenceError
from django.views.decorators.csrf import csrf_exempt

import pandas as pd
import numpy as np


class TextInputForm(forms.Form):
    answer = forms.CharField(label='Ваш ответ', max_length=500)


class MultipleChoiceForm(forms.Form):
    def __init__(self, *args, choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        default_choice = [('', '---------')]
        if choices is not None:
            default_choice.extend(choices)
        self.fields['answer'] = forms.ChoiceField(
            choices=default_choice,
            widget=forms.Select,
            label='Ваш ответ'
        )


def index_page(request):
    return render(request, 'Application.html')


def about_page(request):
    return render(request, 'About.html')


@csrf_exempt
def text_view(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    text = request.POST.get('text')
    difficulty = request.POST.get('difficulty')

    try:
        proc = Processing()
        sentences = proc.process_text(raw_text=text)
        proc.language_checking(sentences)
        request.session['text'] = text
        request.session['difficulty'] = difficulty
        return JsonResponse({'success': True})
    except TooManySentencesError:
        return JsonResponse({'success': False, 'error': 'TooManySentencesError'})
    except NoEnglishSentenceError:
        return JsonResponse({'success': False, 'error': 'NoEnglishSentenceError'})


def write_tasks(request):
    text = request.session.get('text')
    difficulty = request.session.get('difficulty')

    if not text:
        return render(request, 'Application.html')

    # Гарантируем наличие session key
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    try:
        proc = Processing()
        sentences = proc.process_text(raw_text=text)
        proc.language_checking(sentences)
    except (TooManySentencesError, NoEnglishSentenceError) as e:
        return JsonResponse({'success': False, 'error': str(e)})

    task = Tasks(proc)
    data = task.make_tasks(sentences, difficulty)

    # Удаляем только записи этой сессии, не всех подряд
    Sentences.objects.filter(session_key=session_key).delete()

    counter = 1
    forms_list = []
    sentence_ids = []

    for i in range(len(data)):
        if pd.notna(data.loc[i, 'answer']):
            new_sentence = Sentences(
                session_key=session_key,
                sentence=data.loc[i, 'sentence'],
                title=f'Задание № {counter}',
                description=data.loc[i, 'description'],
                answer=data.loc[i, 'answer']
            )
            counter += 1
            if pd.notna(data.loc[i, 'options']):
                options = data.loc[i, 'options']
                choices_list = options.split('//')
                choices = [(choice, choice) for choice in choices_list]
                form_to_display = MultipleChoiceForm(choices=choices)
            else:
                form_to_display = TextInputForm()
        else:
            new_sentence = Sentences(
                session_key=session_key,
                sentence=data.loc[i, 'sentence'],
                title=np.nan,
                description=np.nan,
                answer=np.nan
            )
            form_to_display = None

        new_sentence.save()
        forms_list.append(form_to_display)
        sentence_ids.append(new_sentence.id)

    sentence_form_pairs = zip(
        Sentences.objects.filter(session_key=session_key),
        forms_list,
        sentence_ids
    )
    return render(request, 'Exercises.html', context={'sentence_form_pairs': sentence_form_pairs})


def take_answers(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    sentence_id = request.POST.get('sentence_id')
    answer = request.POST.get('answer')

    if sentence_id is None:
        return JsonResponse({'status': 'error', 'message': 'sentence_id must be provided'})

    session_key = request.session.session_key

    try:
        sentence = Sentences.objects.get(id=sentence_id, session_key=session_key)
        sentence.result = answer
        sentence.save()

        if answer:
            return JsonResponse({
                'status': 'success' if sentence.answer == sentence.result else 'wrong',
                'id': sentence.id
            })
        else:
            return JsonResponse({'status': 'empty', 'id': sentence.id})

    except Sentences.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Sentence does not exist'})
