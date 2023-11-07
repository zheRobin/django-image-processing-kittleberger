from django.conf import settings
from lxml import etree as ET
import json
import requests
from rembg import remove
from PIL import Image,ImageFilter
from io import BytesIO
import time
from app.util import *
import os
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
def stream_results(self, cursor, regex):
    for document in cursor:
        linked_products = document.get("linked_products", [])
        cdn_urls = document.get('CDN_URLS')
        
        if not cdn_urls:
            continue

        for product in linked_products:
            document_id = str(document.get('_id', ''))
            product_key = product.get('mfact_key', '')
            product_name = product.get('name', '')

            if regex is not None and not (regex.search(product_key) or 
                               regex.search(product_name)):
                continue

            matched_product_data = {
                'document_id' : document_id,
                'article number': product_key,
                'name': product_name,
                'cdn_urls': cdn_urls
            }
            
            yield json.dumps(matched_product_data) + "\n"
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

def combine_images(background_url, articles):
    img_name = str(int(time.time())) + '.png'
    local_path = os.path.join(STATIC_URL, img_name)
    background = Image.open(BytesIO(requests.get(background_url).content))
    articles = sorted(articles, key=lambda x: x.get('z_index', 0))
    for article in articles:
        response = requests.get(article['url'])
        img = Image.open(BytesIO(response.content)).resize((article['width'], article['height']))
        product_bbox = img.split()[-1].filter(ImageFilter.MinFilter(3)).getbbox()
        product = img.crop(product_bbox)
        shadow = get_shadow(product)
        shadow.putdata([(10, 10, 10, 10) if item[3] > 0 else item for item in shadow.getdata()])
        shadow_left = article['left'] - (shadow.width - product.width)
        shadow_top = article['top'] + (product.height - shadow.height)
        background.paste(shadow, (shadow_left, shadow_top), shadow)
        background.paste(product, (article['left'], article['top']), product)
    background.save(local_path)

    return local_path