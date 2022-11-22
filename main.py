import sys
import re
import ssl
from io import BytesIO
import pandas as pd
from PIL import Image
from urllib.request import urlopen
from loguru import logger

from fastapi import FastAPI, HTTPException, File, Form
from fastapi.responses import StreamingResponse

import xlsxwriter


# logger
config = {
    "handlers": [
        {"sink": sys.stderr, "backtrace": False},
        {"sink": "logs/runtime.{time:YYYY-MM-DD}.log",
                 "level": "DEBUG",
                 "rotation": "daily",
                 "retention": "1 month",
                 "backtrace": False,
                 "enqueue": True},
        {"sink": "logs/errors.{time:YYYY-MM-DD}.log",
                 "level": "WARNING",
                 "rotation": "daily",
                 "retention": "1 month",
                 "backtrace": False,
                 "enqueue": True},
    ]
}
logger.configure(**config)


'''Fast API
'''
VERSION = '0.1'
TITLE = 'xlsx2image'
app = FastAPI(title=TITLE, version=VERSION)
logger.info('=' * 10 + ' Init app[{}@{}] '.format(TITLE, VERSION) + '=' * 10)


def is_url(url):
    """Return True if string is an http or ftp path."""
    url_regex = re.compile(r'http://|https://|ftp://|file://|file:\\')
    return (isinstance(url, str) and
            url_regex.match(url) is not None)



@app.post(f"/{TITLE}/")
async def handle(file: bytes = File(), url_index: str = Form()):
    logger.info('Recive excel file...')
    if len(file):
        pd_df = pd.read_excel(file, dtype=str)
        pd_df.reset_index()
        logger.info("Read excel file from pd.read_excel('', dtype=str)")
        if url_index in pd_df.keys():
            ssl._create_default_https_context = ssl._create_unverified_context  # disable ssl
            url_row_num = pd_df.keys().get_loc(url_index)
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output, {'nan_inf_to_errors': True})
            cell_format = workbook.add_format()
            cell_format.set_align('center')
            cell_format.set_align('vcenter')
            worksheet = workbook.add_worksheet()

            logger.info('Finish create workbook...')

            # Add header
            for col_idx, col_header in enumerate(pd_df.keys()):
                worksheet.write(0, col_idx, col_header)

            logger.info('Add col_header to worksheet done.')

            for row_idx, row in pd_df.iterrows():
                for col_idx, value in enumerate(row):
                    logger.info(f'row: [{row_idx + 1}/{len(pd_df)}], col: [{col_idx}/{len(row)}]')
                    if col_idx != url_row_num or pd.isna(value):
                        worksheet.write(row_idx + 1, col_idx, value, cell_format)
                    else:
                        # url and not na value
                        urls = value.split(',')  # split by common
                        url_idx = 0
                        for url in urls:
                            if is_url(url):
                                img = None
                                try:
                                    data = BytesIO(urlopen(url, timeout=15).read())
                                    img = Image.open(data)
                                except Exception as e:
                                    logger.error(e)

                                if img is None:
                                    continue
                                else:
                                    w, h = img.size

                                    worksheet.set_column_pixels(col_idx + url_idx, col_idx + url_idx, 112)
                                    worksheet.set_row_pixels(row_idx + 1, 199)
                                    worksheet.insert_image(row_idx + 1,
                                                           col_idx + url_idx,
                                                           url,
                                                           {'image_data': data,
                                                            'x_scale': 112 / w,
                                                            'y_scale': 199 / h})
                                    url_idx += 1

            workbook.close()
            output.seek(0)
            logger.info('Close workbook...')
            headers = {
                'Content-Disposition': 'attachment; filename="xlsx2image.xlsx"'
            }
            return StreamingResponse(output, headers=headers)

        else:
            info = f'Excel表中没有 [{url_index}] 列标题。'
            logger.error(info)
            return HTTPException(status_code=405, detail=info)

    else:
        info = f'文件大小为0，请检查文件或网络。'
        logger.error(info)
        return HTTPException(status_code=406, detail=info)

