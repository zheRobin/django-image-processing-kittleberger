from django.conf import settings
from lxml import etree as ET
import json
import requests
from rembg import remove
from PIL import Image,ImageFilter
from io import BytesIO
import os, time, base64
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
def upload(in_path, out_path):
    with open(in_path, 'rb') as f:
        file_link = s3_upload( f, out_path)
    return file_link
def remove_background(input_path):
    response = requests.get(input_path)
    input_img = response.content
    img_name =  str(int(time.time())) + '.png'
    local_path = os.path.join(STATIC_URL,img_name)
    output_img = remove(input_img)
    img = Image.open(BytesIO(output_img))
    img.save(local_path, "PNG")
    return img_name
def save_origin(input_path):
    response = requests.get(input_path)
    input_img = response.content
    img_name =  str(int(time.time())) + '.png'
    local_path = os.path.join(STATIC_URL,img_name)
    img = Image.open(BytesIO(input_img))
    img.save(local_path, "PNG")
    return img_name
def resize_save_img( img, size, type, output_path, resolution_dpi):
    img = Image.open(img)
    img_name =  str(int(time.time())) + '.png'
    local_path = os.path.join(STATIC_URL,img_name)
    output_img = img.resize(size)
    output_img.save(local_path, type, dpi=(resolution_dpi, resolution_dpi))
    result = upload( local_path, output_path)
    return result
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
def save_product_image(base64_img):
    img_format = base64_img.split(';')[0].split('/')[1]
    img_name = str(int(time.time())) + '.' + img_format
    local_path = os.path.join(STATIC_URL, img_name)
    output_path = '/mediafils/transparent_image/'+img_name
    img_data = base64.b64decode(base64_img.split(',')[1])
    with open(local_path, 'wb') as f:
        f.write(img_data)
    result = upload( local_path, output_path)
    return result
def compose_render(template, articles):
    background = Image.open(BytesIO(requests.get(template.bg_image_cdn_url).content)).resize((template.resolution_width, template.resolution_height))
    articles = sorted(articles, key=lambda x: x.get('z_index', 0))
    for article in articles:
        response = requests.get(article['article_link']).content
        if article['is_transparent'] == "true":
            media = Image.open(BytesIO(remove(response)))
        else:
            media = Image.open(BytesIO(response))
        img = media.resize((int(article['width']), int(article['height'])))
        product_bbox = img.split()[-1].filter(ImageFilter.MinFilter(3)).getbbox()
        product = img.crop(product_bbox)
        if template.is_shadow:
            shadow = get_shadow(product)
            shadow.putdata([(10, 10, 10, 10) if item[3] > 0 else item for item in shadow.getdata()])
            shadow_left = article['left'] - (shadow.width - product.width)
            shadow_top = article['top'] + (product.height - shadow.height)
            background.paste(shadow, (shadow_left, shadow_top), shadow)
        background.paste(product, (article['left'], article['top']), product)
    buffered = BytesIO()
    background.save(buffered, format=template.file_type, dpi=(template.resolution_dpi, template.resolution_dpi))
    base64_img = base64.b64encode(buffered.getvalue())
    img_data = f"data:image/{template.file_type.lower()};base64,{base64_img.decode('utf-8')}"
    return img_data