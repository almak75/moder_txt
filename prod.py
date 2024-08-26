from craft_text_detector import Craft
import asyncio



#это нужно исключительно для видео. для отдельных фото - ничего этого не надо.
import cv2          #этим читаем видеофайл. медленная, тупая, но работает...очень медленно читает избавиться бы от нее.
CONTROL_STEP = 10   #используется для анализа видео, чтобы не анализировать все кадры.  Это шаг, через который анализируются кадры для снижения нагрузки
                    #если в этом кадре будет найден текст, то проанализируются все кадры слева и справа
                    #если текст найден не будет, то шагнем дальше
CAN_SKIP = 24       #по  результатам анализа - у нас будут диапазоны кадров, где найден текст. 
                    #Пропуск - указываем допустимое количество кадров, которое может быть между диапазонами, чтобы они считались разными.
                    #если кадров меньше то считаем, что диапазон один (два диапаазона склеятся в один)
                    #Если кадров больше - от диапазоны останутся независимыми


#модель - общая для изображения и видео. 
output_dir = None   #не будем сохранять найденные вырезки текстов
THRESHOLD = 0.88 #этот параметрт определяет уверенность в тексте, если его уменьшать, могут полезть ложно положительные детекции. Если увеличить - то он что-то может потерять. 
craft = Craft(output_dir=output_dir, text_threshold = THRESHOLD, crop_type="poly", cuda=True, rectify = False) #модель
        
#====================================================================================
#====================================================================================
#=================ДАЛЕЕ ПРОЦЕДУРЫ И ФУНКЦИИ ДЛЯ ОБРАБОТКИ ВИДЕО======================
#====================================================================================
#====================================================================================


async  def get_predict_from_model(image):
    prediction_result = craft.detect_text(image)   #забираем результат
    
    list_of_lists  =  list(prediction_result['boxes']) #список всех полученных полигонов
    find_boxes = len(list_of_lists) #количество полученных полигонов. Если их ноль, то значит ничено нет. Нам надо 0 - нет, 1 если есть. там возвращается куча всего, можно тексты вырезать
    if  find_boxes:
        find_boxes = 1
    return  find_boxes


#ФУНКЦИЯ ОБРАБОТКИ ИЗОБРАЖЕНИЙ
async def look_to_file(img):
    rez = await asyncio.gather(
       get_predict_from_model(img),
       )
    return {'need_moderation':rez}

#====================================================================================
#====================================================================================
#=============================ДАЛЕЕ ФУНКЦИИ ДЛЯ ОБРАБОТКИ ВИДЕО======================
#====================================================================================
#====================================================================================


def split_list_by_delimiter(A, delimiter=0):
    #делит список на подсписки. Границей подсписков в списке А является ноль. 
    #Например, было: [1, 2, 3, 0, 0, 0, 7, 8, 9, 0, 0, 12, 13, 0, 15, 16, 0]
    #Станет: [(1, 3), (7, 9), (12, 13), (15, 16)]
    
    
    sublists = []                                               # Инициализация списка для подсписков и временного подсписка
    current_sublist = []
    
    for element in A:
        if element == delimiter: 
            if current_sublist:                                 # Добавление текущего подсписка в список подсписков, если он не пуст
                sublists.append(current_sublist)
                current_sublist = []                            # чистим, потом начинаем сначала
        else:
            current_sublist.append(element)                     # Добавление элемента в текущий подсписок
    
    if current_sublist:                                         # Добавление последнего подсписка, если он не пуст
        sublists.append(current_sublist)
    
    return sublists

def prepair_timeslot(fr):                                       #это самая красивая процедура в этом модуле. моя гордость.
    number_frames = len(fr)                                     #количество кадров
    tmp = [i if fr[i] else -1 for i in range(number_frames)]    #подставляем номер кадра вместо 1 и -1 если кадр без текста
    tmp = split_list_by_delimiter(tmp,-1)                           #делим список на подсписки по разделителю (-1). Сначала разделителем был 0, нно потом я ушел от этого
    tmp = [(i[0], i[-1]) for i in tmp]                          #создаем таймслоты - первый и последний кадр в слоте
    return tmp



#async def look_to_video_file(temp_file):
def look_to_video_file(temp_file):

    video = cv2.VideoCapture(temp_file)                         #открываем файл с видео
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = video.get(cv2.CAP_PROP_FPS)                           #это будет нужно, чтобы определить на какой секунде начинается и заканчивается текст.
                                                                #левую границу будем округлять до секунды в меньшую сторону, правую в правую
    
   
    control = set() #что еще надо допроверить. здесь будут кадры, которые надо проверить слева и справа от найденного кадра с текстом.
    fr =[0] * total_frames #список со всеми кадрами
    prev = 0
    for frame_number in range(0,total_frames, CONTROL_STEP):
        video.set(cv2.CAP_PROP_POS_FRAMES, frame_number) #позиционируемся на нужном кадре
        ret, frame = video.read()
        #смотриим, что там за кадр. для работы это не нужно, болььше для отладки
        # cv2.imwrite(f'Y:\{frame_number}.jpg', frame)
        if not ret:
            break
        
        prediction_result = craft.detect_text(frame)
        
        list_of_lists  =  list(prediction_result['boxes'])
        
        find_boxes = len(list_of_lists)
        if find_boxes:
           fr[frame_number] = 1  #если нет, то останется 0- значит кадр прошел можерацию и текста там нет
           #мы нашли кадр в котором есть текст. Автоматически добавляем все кадры слева и справ от него для проверки, 
           #но проверять будем позже, иначе алгоритм слишком усложняется, так как могут прилететь кадры еще и со следующей точки
           new_control_lev = list(range(prev + 1,frame_number)) #левая граница диапазона от нашего кадра
           new_control_prav = list(range(frame_number+1,frame_number + CONTROL_STEP)) #правая граница диапазона до следующего ключевого кадра, но без него самого, но он будет в след.итерации проверен
           
           control.update(set(new_control_lev))     #эти кадры проверим потом
           control.update(set(new_control_prav))    #эти кадры проверим потом
        prev = frame_number
    #проверим - если все 0, то дальше не надо ничего обрабатывать, уходим отсюда, модерация не нужна
    if  all(x == 0 for x in fr):
        # print('Все кадры без текста')
        return {'need_moderation':0}    
    
    #теперь проверим все кадры, которые ранее копили. это как раз замедляет это в худжем случае может приводить к полной проверке видео, теоретически - это позволяет только найти границы таймлота
    #но вообще видео уже должно отправиться на проверку
    #   
    for frame_number in control:
        #берем кадр из сета, встаем на него, читаем и проверяем, если с текстом, то ставим 1 в номере    
        video.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame2 = video.read()
        #print(frame_count)
        # Если кадр прочитан успешно, ret будет True
        if not ret:
            #print('Не читается кадр с номеро',frame_number)
            continue
        
        #cv2.imwrite(f'Y:\{frame_number}.jpg',frame2)
        
        prediction_result = craft.detect_text(frame2)
        list_of_lists  =  list(prediction_result['boxes'])
        find_boxes = len(list_of_lists)
        if find_boxes:
            fr[frame_number] = 1
    
      
    #теперь надо близкие диапазоны объединить
    ind = len(fr)
    control = []
    i = 0
    while i<ind:
        if fr[i]: 
            if len(control)<= CAN_SKIP:     #надо заменить все  на 1,  Про  CAN_SKIP читайте выше
                for m in control:
                    fr[m]=1
            control=[]
        else: #получили 0
            control.append(i)
        i += 1
    if len(control)<= CAN_SKIP:             #хвост может остаться
        for m in control:
            fr[m]=1
    
            
    control=[]
    

    #Теперь у нас есть fr. он соответствует каждому кадру. там 0 - кадр без текста, 1 - кадр с текстом.
    #нам нужно разбить это на диапазоны, (,),(,),(,), где первое число - первый кадр с текстом, второе число - последний кадр с текстом. Нули - это границы диапазонов с учетом CAN_SKIP

    timeslots = prepair_timeslot(fr)  #
    
    #теперь у нас есть тайсмслоты вида [(s1,f1),(s2,f2),(s3,f3),...,(sN,fN)]
    #пример [[0, 302], [410, 493]]
    #первое число - это кадр, который надо вытащить из видео и отправить его. 
    #делаем такую структуру: {{'timesslot':[s1,f1], 'frame_data':ZZZ},}
    #ZZZ - это  надо jpg превратить в список и списком его передать.... на принимающей  стороне его раскодировать из списка обратно в JPG
    
    
    frames_data = [] #тут будем формировать структуру
    for timeslot in timeslots:
        key_frame = timeslot[0] #номер кадра, который нам надо отправить в ответ
        video.set(cv2.CAP_PROP_POS_FRAMES, key_frame)
        ret, frame = video.read()
        if ret:
            # Конвертируем изображение в формат JPEG для отправки
            _, jpeg_frame = cv2.imencode('.jpg', frame)
            
            # Добавляем номер кадра и данные изображения в список результатов
            frames_data.append({
                #'timesslot': timeslot,  #если оставить так, то в ответ уйдут номера кадров начала и окончания таймслота
                'fps':fps,
                'timesslotF': timeslot,
                'timesslot': [int(timeslot[0] // fps), int(timeslot[1] // fps+1)], #так уйдут секунды. Округляем до целой секунды. Левую границу вниз, правую границу вверх
                'frame_data': jpeg_frame.tolist()
            })


    video.release() #отпускаем видео поток
    rez = {'need_moderation':1, 'timeslots':frames_data}

    return rez