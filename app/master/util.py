from django.conf import settings
from lxml import etree as ET
import json
import requests
from rembg import remove
from PIL import Image
from io import BytesIO
import time
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
            # document_id = document.get('_id', '')
            product_key = product.get('mfact_key', '')
            product_name = product.get('name', '')

            if regex is not None and not (regex.search(product_key) or 
                               regex.search(product_name)):
                continue

            matched_product_data = {
                'document_id' : str(document.get('_id')),
                'article number': product_key,
                'name': product_name,
                'cdn_urls': cdn_urls
            }
            
            yield json.dumps(matched_product_data) + "\n"
def remove_background(self, input_path):
    response = requests.get(input_path)
    input_img = response.content
    output_path = STATIC_URL + '\\'+ str(int(time.time())) + '.png'
    output_img = remove(input_img)
    img = Image.open(BytesIO(output_img))
    img.save(output_path, "PNG")
    return output_path