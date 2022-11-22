FROM python:3.9

COPY . /root/workspace/Xlsx2Image

RUN pip config set global.index-url https://mirrors.bfsu.edu.cn/pypi/web/simple && \
    pip install --no-cache-dir --upgrade -r /root/workspace/Xlsx2Image/requirements.txt

WORKDIR /root/workspace/Xlsx2Image

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]