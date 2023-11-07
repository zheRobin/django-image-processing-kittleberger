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
    alpha = img.split()[-1]
    alpha = alpha.filter(ImageFilter.MinFilter(3))
    shape = Image.new('RGBA', alpha.size, (200, 200, 200, 230))
    shape.putalpha(alpha)
    segmented = Image.new('RGBA', (shape.size[0], shape.size[1]//4))
    segmented.paste(shape, (0, -(shape.size[1]//4)*3))
    shape = shape.resize((shape.size[0], shape.size[1]//4), Image.NEAREST)
    cx, cy = -0.8, 0
    c = 1 + shape.height / shape.width
    px = (shape.width/20)*(img.height/img.width)
    py = shape.height*0.08
    shadow = segmented.transform(shape.size, method=Image.AFFINE,data=[c, cx, -px, cy, 1.1, -py], resample=Image.BICUBIC)
    shadow = shadow.resize((int(shadow.size[0]*c), shadow.size[1]))
    return shadow

def combine_images(background_url, product_url, product_height, product_width, left, top):
    img_name =  str(int(time.time())) + '.png'
    local_path = os.path.join(STATIC_URL,img_name)
    response = requests.get(background_url)
    background = Image.open(BytesIO(response.content))
    response = requests.get(product_url)
    product = Image.open(BytesIO(response.content))
    product = product.resize((product_width,product_height))
    shape = product.split()[-1]
    shape = shape.filter(ImageFilter.MinFilter(3))
    bbox = shape.getbbox()
    product = product.crop(bbox)
    shadow = get_shadow(product)
    shadow_left = left - (shadow.size[0] - product.size[0])
    shadow_top = top + (product.size[1] - shadow.size[1])
    background.paste(shadow, (shadow_left, shadow_top), shadow)
    background.paste(product, (left, top), product)
    background.save(local_path)
    return local_path
