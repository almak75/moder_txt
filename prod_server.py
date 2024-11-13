#from typing import Optional
from PIL import Image
from io import BytesIO
#from pydantic import BaseModel#это понадобилось для втрого варианта
#нужно для работы с файлами с айфона
from pillow_heif import register_heif_opener

from datetime import datetime
import os
import numpy as np
from fastapi import FastAPI, File, UploadFile, Form
import gc
import asyncio
from tempfile import NamedTemporaryFile




register_heif_opener()

import prod #в этом  файле хранятся все процедуры

app = FastAPI()

IND = 0

@app.post("/ps")
async def analyze_image1(image: UploadFile = File(...)):
    global IND
    IND += 1
   
      
        
    with Image.open(BytesIO(await image.read())) as img:
          
        if img.mode != 'RGB':
            img = img.convert("RGB")
        img_np = np.array(img)
        pok= await prod.look_to_file(img_np)
    if IND >= 500:
        IND = 0
        gc.collect() #почистимся 
    return pok #у нас только 1 картинка, так что отдаем только первый ответ
    

#import ffmpeg

# class VideoParams(BaseModel):
#     step: int
#     mode: int
#     fast_terminate: int



@app.post("/vd")
async def analyze_video(video: UploadFile = File(...),
                        step: int = Form(default=10),
                      mode: int = Form(default=0)
                        ):
    global IND
    IND += 1

    #STEP = 10   #используется для анализа видео, чтобы не анализировать все кадры.  Это шаг, через который анализируются кадры для снижения нагрузки
                    #если в этом кадре будет найден текст, то проанализируются все кадры слева и справа
                    #если текст найден не будет, то шагнем дальше
    # mode = 0 - получение таймслотов
    # mode = 1 - самый быстрый способ - ищем через step первый шаг с текстов и выходим из поиска   
    # mode = 2 - ищем через step все кадры и возвращаем тогда только найденные секунды, где есть текcт
    

    filename = video.filename
    # Разделяем имя файла на имя и расширение
    _, extension = os.path.splitext(filename)
    
    video_file = await video.read()
    temp_file = NamedTemporaryFile(delete=False, suffix=extension)
    temp_file.write(video_file)

   
    pok = prod.look_to_video_file(temp_file.name, step, mode)
    #pok = 1
    temp_file.close()
    os.remove(temp_file.name)  #удаляем временный файл
    if IND >= 100:
            IND = 0   
            gc.collect() #почистимся 
    
    return pok
    








@app.post("/test")
async def analyze_image(image: UploadFile = File(...)):
    with Image.open(BytesIO(await image.read())) as img:
         current_datetime = datetime.now()
         str_current_datetime = current_datetime.strftime("%Y-%m-%d %H-%M-%S")
         filename = f"inp_{str_current_datetime}.jpg"
         filename = os.path.join('arh', filename)
         #img.save(filename)
         return {"width": img.width, "height": img.height}



txt = 'Этот адрес url не предназначен для открытия в браузере. Используйте post запрос в формате requests.post(url, files=file) где - file - это бинарный файл с изображением для распознавания'



@app.get("/ps")
async def not_use():
   
   
    return txt

@app.get("/test")
async def not_use():
   
    return txt

#app.include_router(router)
