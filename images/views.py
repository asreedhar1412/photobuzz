from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ImageCreateForm
from django.shortcuts import get_object_or_404
from .models import Image
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from common.decorators import ajax_required
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, \
                                  PageNotAnInteger
from actions.utils import create_action
from django.conf import settings
import json
from watson_developer_cloud import ToneAnalyzerV3
from watson_developer_cloud import LanguageTranslatorV2 as LanguageTranslator


@login_required
def image_create(request):
    if request.method == 'POST':
        # form is sent
        form = ImageCreateForm(data=request.POST)
        if form.is_valid():
            # form data is valid
            cd = form.cleaned_data
            new_item = form.save(commit=False)

            # assign current user to the item
            new_item.user = request.user
            new_item.save()
            create_action(request.user, 'bookmarked image', new_item)
            messages.success(request, 'Image added successfully')

            # redirect to new created item detail view
            return redirect(new_item.get_absolute_url())
    else:
        # build form with data provided by the bookmarklet via GET
        form = ImageCreateForm(data=request.GET)

    return render(request,
                  'images/image/create.html',
                  {'section': 'images',
                   'form': form})

def image_detail(request, id, slug):
    image = get_object_or_404(Image, id=id, slug=slug)
    tone_analyzer = ToneAnalyzerV3(
        username='176a2db1-fc8e-48c2-a85c-cc5b640569a2',
        password='HRfyi175CWo0',
        version='2017-09-19')

    language_translator = LanguageTranslator(
        username='d5a5b0d1-c7b8-40f0-8ac7-bcb6f5b364a3',
        password='IfEtTfRMi1EG')

    data = json.dumps(tone_analyzer.tone(text=image.description),
                      indent=1)  # converting to string and storing in the data
    j = json.loads(data)
    image.info = j['document_tone']['tone_categories'][0]['tones']
    # post.info = json.dumps(post.info);
    image.angerScore = image.info[0]['score']
    image.disgustScore = image.info[1]['score']
    image.fearScore = image.info[2]['score']
    image.joyScore = image.info[3]['score']
    image.sadScore = image.info[4]['score']
    translation = language_translator.translate(text=image.description, source='en', target='fr')
    image.translatedText = json.dumps(translation, indent=2, ensure_ascii=False)
    return render(request,
                  'images/image/detail.html',
                  {'section': 'images',
                   'image': image})

@ajax_required
@login_required
@require_POST
def image_like(request):
    image_id = request.POST.get('id')
    action = request.POST.get('action')
    if image_id and action:
        try:
            image = Image.objects.get(id=image_id)
            if action == 'like':
                image.users_like.add(request.user)
                create_action(request.user, 'likes', image)
            else:
                image.users_like.remove(request.user)
            return JsonResponse({'status':'ok'})
        except:
            pass
    return JsonResponse({'status':'ko'})

@login_required
def image_list(request):
    images = Image.objects.all()
    paginator = Paginator(images, 8)
    page = request.GET.get('page')
    try:
        images = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer deliver the first page
        images = paginator.page(1)
    except EmptyPage:
        if request.is_ajax():
            # If the request is AJAX and the page is out of range
            # return an empty page
            return HttpResponse('')
        # If page is out of range deliver last page of results
        images = paginator.page(paginator.num_pages)
    if request.is_ajax():
        return render(request,
                      'images/image/list_ajax.html',
                      {'section': 'images', 'images': images})
    return render(request,
                  'images/image/list.html',
                   {'section': 'images', 'images': images})

