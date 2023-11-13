from django.conf import settings
from lxml import etree as ET
import json
import requests
from rembg import remove
from PIL import Image,ImageFilter
from io import BytesIO
import os, time, io
from app.util import *
ATTRIBUTES_XPATH = ET.XPath('.//attribute')
LINKED_PRODUCTS_XPATH = ET.XPath('.//linked_products/product')
LINKED_PRODUCT_ATTRIBUTES_XPATH = ET.XPath('.//attributes/attribute')
VALUE_XPATH = ET.XPath('./value/text()')
STATIC_URL = settings.STATIC_ROOT
def convert(element):
    attributes = {attribute.get('ukey'): VALUE_XPATH(attribute) for attribute in ATTRIBUTES_XPATH(element)}

    linked_products = [{'id': product.get('id'), 
                        'name': product.get('name'), 
                        'mfact_key': product.get('mfact_key'), 
                        'attributes': {product_attr.get('ukey'): VALUE_XPATH(product_attr) for product_attr in LINKED_PRODUCT_ATTRIBUTES_XPATH(product)} } 
                       for product in LINKED_PRODUCTS_XPATH(element)]
    result = {
        'id': element.get('id'), 
        'name': element.get('name'), 
        'linked_products': linked_products
    }

    result.update(attributes)
    return result
def stream_results(self, cursor, regex, page):
    total_yield = 0
    limit = 100
    skip = limit * (page-1) * 10
    chunk = []
    cursor.skip(skip)
    for document in cursor:
        if total_yield >= limit:
            break

        cdn_urls = document.get('CDN_URLS')
        linked_products = document.get("linked_products", [])

        if cdn_urls and linked_products:
            document_id = str(document.get('_id', ''))
            chunk = [{'document_id' : document_id,'article_number': product.get('mfact_key', ''),'name': product.get('name', ''),'cdn_urls': cdn_urls} 
                     for product in linked_products if regex is None or regex.search(product.get('mfact_key', '')) or regex.search(product.get('name', ''))]

            while len(chunk) >= 10 and total_yield < limit:
                yield json.dumps(chunk[:10]) + '\n\n'
                total_yield += 1
                chunk = chunk[10:]
    if chunk and total_yield < limit:
        yield json.dumps(chunk) + '\n\n'
    if not chunk and total_yield < limit:
        yield json.dumps([]) + '\n\n'
def remove_background(self, input_path):
    response = requests.get(input_path)
    input_img = response.content
    img_name =  str(int(time.time())) + '.png'
    local_path = os.path.join(STATIC_URL,img_name)
    output_path = '/mediafils/transparent_image/'+img_name
    output_img = remove(input_img)
    img = Image.open(BytesIO(output_img))
    img.save(local_path, "PNG")
    with open(local_path, 'rb') as f:
        file_link = s3_upload(self, f, output_path)
    return file_link
def save_img(self, img, size, type, output_path):
    img = Image.open(img)
    img_name =  str(int(time.time())) + '.png'
    local_path = os.path.join(STATIC_URL,img_name)
    output_img = img.resize(size)
    output_img.save(local_path, type)
    with open(local_path, 'rb') as f:
        file_link = s3_upload(self, f, output_path)
    return file_link

def get_shadow(img):
    img_alpha = img.split()[-1].filter(ImageFilter.MinFilter(3))
    img_shape = Image.new('RGBA', img_alpha.size)
    img_shape.putalpha(img_alpha)
    segmented = Image.new('RGBA', (img_shape.size[0], img_shape.size[1]//4))
    segmented.paste(img_shape, (0, -(img_shape.size[1]//4)*3))
    c = 1 + segmented.height / segmented.width
    px = (segmented.width/20)*(img.height/img.width)
    py = segmented.height*0.08

    shadow = segmented.transform(segmented.size, method=Image.AFFINE, data=[c, -0.8, -px, 0, 1.1, -py], resample=Image.BICUBIC)
    shadow = shadow.resize((int(shadow.width*c), shadow.height)).filter(ImageFilter.GaussianBlur(radius=3))
    return shadow

def combine_images(self,template, articles):
    img_name = str(int(time.time())) + '.png'
    local_path = os.path.join(STATIC_URL, img_name)
    output_path = 'mediafils/transparent_image/'+img_name
    background = Image.open(BytesIO(requests.get(template.bg_image_cdn_url).content)).resize((template.resolution_width, template.resolution_height))
    articles = sorted(articles, key=lambda x: x.get('z_index', 0))
    for article in articles:
        if template.is_shadow and article['transparent_cdn_url']:
            response = requests.get(article['transparent_cdn_url'])
        else:
            response = requests.get(article['cdn_url'])
        img = Image.open(BytesIO(response.content)).resize((int(article['width']*article['scaling']), int(article['height']*article['scaling'])))
        product_bbox = img.split()[-1].filter(ImageFilter.MinFilter(3)).getbbox()
        product = img.crop(product_bbox)
        if template.is_shadow:
            shadow = get_shadow(product)
            shadow.putdata([(10, 10, 10, 10) if item[3] > 0 else item for item in shadow.getdata()])
            shadow_left = article['prod_left'] - (shadow.width - product.width)
            shadow_top = article['prod_top'] + (product.height - shadow.height)
            background.paste(shadow, (shadow_left, shadow_top), shadow)
        background.paste(product, (article['prod_left'], article['prod_top']), product)
    background.save(local_path)
    # thumbnail = background.thumbnail((300, int(300*template.resolution_height//template.resolution_width)), Image.ANTIALIAS)
    with open(local_path, 'rb') as f:
        file_link = s3_upload(self, f, output_path)
    return file_link