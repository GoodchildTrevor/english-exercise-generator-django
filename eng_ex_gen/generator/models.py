from django.db import models


class Sentences(models.Model):
    session_key = models.CharField(max_length=40, db_index=True, default='')
    sentence = models.CharField(max_length=10000, blank=False)
    title = models.CharField(max_length=200, default='Default', blank=True)
    description = models.CharField(max_length=1000, default='Default', blank=True)
    answer = models.CharField(max_length=1000, default='Default', blank=True)
    result = models.CharField(max_length=1000, default='Default', null=True, blank=True)
