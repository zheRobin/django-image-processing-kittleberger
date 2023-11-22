from django.conf import settings
from lxml import etree as ET
from urllib.parse import urlparse
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
        file_link = s3_upload(f, out_path)
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
def resize_save_img(img, size, type, output_path, resolution_dpi):
    img = Image.open(img)
    if img.mode not in ('RGB', 'RGBA') or (img.mode == 'RGBA' and type.upper() != 'PNG'):
        img = img.convert("RGB")
    format = 'PNG' if type == 'TIFF' else type
    img_name = str(int(time.time())) + '.' + format.lower()
    local_path = os.path.join(STATIC_URL, img_name)
    output_img = img.resize(size)
    output_img.save(local_path, format.upper(), dpi=(resolution_dpi, resolution_dpi))
    result = upload(local_path, output_path+img_name)
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
    output_path = 'mediafiles/compose/'+img_name
    if base64_img and ',' in base64_img:
        img_data = base64.b64decode(base64_img.split(',')[1])
    else:
        return Response(error("Invalid base64_img"))
    with open(local_path, 'wb') as f:
        f.write(img_data)
    result = upload( local_path, output_path)
    return result

def compose_render(template, articles):
    background = Image.open(BytesIO(requests.get(template.bg_image_cdn_url).content))
    articles = sorted(articles, key=lambda x: x.get('z_index', 0))
    
    for article in articles:
        response = requests.get(article['article_link']).content
        if article['is_transparent'] == True or article['is_transparent']:
            media = Image.open(BytesIO(remove(response)))
        else:
            media = Image.open(BytesIO(response))

        if (article.get('width') is not None and
            article.get('height') is not None and
            isinstance(article.get('width'), (int, float)) and
            isinstance(article.get('height'), (int, float)) and
            media.width != 0 and media.height != 0):

            ratio = min(int(article['width']) / media.width, int(article['height']) / media.height)
            new_size = tuple(int(dim * ratio) for dim in media.size)
        else:
            new_size = media.size

        img = media.resize(new_size, Image.LANCZOS)
        product_bbox = img.split()[-1].filter(ImageFilter.MinFilter(3)).getbbox()
        product = img.crop(product_bbox)

        if (isinstance(article.get('left'), (int, float)) and 
            isinstance(article.get('top'), (int, float)) and 
            isinstance(article.get('width'), (int, float)) and
            isinstance(article.get('height'), (int, float)) and
            isinstance(product.width, (int, float)) and
            isinstance(product.height, (int, float))):

            left = int(article['left'] + (article['width'] - product.width) / 2)
            top = int(article['top'] + (article['height'] - product.height) / 2)
        else:
            left_value = article.get('left', 0)
            top_value = article.get('top', 0)

            left = int(left_value) if left_value is not None else 0
            top = int(top_value) if top_value is not None else 0

        if template.is_shadow:
            shadow = get_shadow(product)
            shadow.putdata([(10, 10, 10, 10) if item[3] > 0 else item for item in shadow.getdata()])
            shadow_left = left - (shadow.width - product.width)
            shadow_top = top + (product.height - shadow.height)
            background.paste(shadow, (int(shadow_left), int(shadow_top)), shadow)

        if product.mode == "RGBA":
            mask = product.split()[3]
            background.paste(product, (left, top), mask)
        else:
            background.paste(product, (left, top))

    buffered = BytesIO()
    format = 'PNG' if template.file_type == 'TIFF' else template.file_type
    background.save(buffered, format=format, dpi=(template.resolution_dpi, template.resolution_dpi))
    base64_img = base64.b64encode(buffered.getvalue())
    img_data = f"data:image/{format.lower()};base64,{base64_img.decode('utf-8')}"
    return img_data

def conv_tiff(image_or_url):
    if urlparse(image_or_url).scheme in ['http', 'https']:
        response = requests.get(image_or_url, stream=True)
        response.raise_for_status()
        image_data = response.content
    else:
        try:
            image_data = base64.b64decode(image_or_url.split(',')[1])
        except Exception as e:
            raise ValueError("Invalid input, please enter a valid URL or base64 image") from e    

    with BytesIO(image_data) as image_io:
        with Image.open(image_io) as img:
            with BytesIO() as output:
                img.save(output, format='PNG')
                base64_img = base64.b64encode(output.getvalue())
        
    return f"data:image/png;base64,{base64_img.decode('utf-8')}"
def get_tiff(image_or_url):
    if urlparse(image_or_url).scheme in ['http', 'https']:
        response = requests.get(image_or_url, stream=True)
        response.raise_for_status()
        image_data = response.content
    else:
        try:
            image_data = base64.b64decode(image_or_url.split(',')[1])
        except Exception as e:
            raise ValueError("Invalid input, please enter a valid URL or base64 image") from e

    with BytesIO(image_data) as image_io:
        with Image.open(image_io) as img:
            img_dpi = (300, 300)

            with BytesIO() as output:
                img.save(output, format='TIFF', dpi=img_dpi)
                base64_img = base64.b64encode(output.getvalue())

    return f"data:image/tiff;base64,{base64_img.decode('utf-8')}"