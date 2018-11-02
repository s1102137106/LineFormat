# In[import]:
import re
from datetime import datetime, timedelta
import pandas as pd
from db_connection import db_connection
# In[date judgement]:
def is_date(date):
    #date_13 = date[:14]
    #mat = re.search(r"(\d{4}/\d{1,2}/\d{1,2})",date_13)
    #return mat != None and len(date) == 14
    date_10 = date[:10]
    mat = re.search(r"(\d{4}/\d{1,2}/\d{1,2})",date_10)
    return mat != None and len(date) == 16

print(is_date('2018/02/02(Fri)'))

def is_time(time):
    time_7 = time[:7]
    mat = re.search(r"(\d{1,2}:\d{1,2})",time_7)
    return mat != None and (len(time) == 7 or len(time)==5)
is_time('09:48')

'''
def is_time(time):
    time_7 = time[:7]
    mat = re.search(r"(\午\d{1,2}:\d{1,2})",time_7)
    return mat != None and len(time) 
is_time('下午09:48')
'''
# In[Line Model]:
# 將Line純文字對話 轉成結構化資料
class LineModel():
    
    def __init__(self):
        self.content = ''
        self.time = ''
        self.date = ''
        self.user_name = ''
        self.datetime = ''
        
    def set_datetime(self,date,time):
        date = date.replace('日期：','')
        
        #process date
        date = date[:10]
        print(date)
        year = date.split('/')[0]
        month = date.split('/')[1]
        day = date.split('/')[2]
        
        cor_date = datetime(int(year), int(month), int(day))

        
        if '午' in time :
            #process time 2017後的版本
            s =time.split('午')
            hour = s[1].split(':')[0]
            m = s[1].split(':')[1]
      
            if s[0] == '下':
                hour = int(hour)+12
                #下午12點 為12:00
                if hour == 24:
                    hour = '12'
            else:
                #上午12點 為00:00
                if int(hour) == 12:
                    hour = '0'
        else:
            #process time 2018前的版本
            hour = time.split(':')[0]
            m = time.split(':')[1]
        
        
        
        #日期＋時間
        cor_date = cor_date + timedelta(hours=int(hour),minutes=int(m))
        self.datetime = cor_date
    
    def set_user_name(self,user_name):
        self.user_name = user_name
        
    def set_content(self,content):
        if len(content)>250:
            self.content=''
            return ''
        
        if self.content !='':
            self.content = self.content + content
        else:
            self.content=content
    
    def set_line_model(self,date,time,user_name,content):
        self.set_datetime(date,time)
        self.set_user_name(user_name)
        self.set_content(content)
    
    #儲存成pd的格式 三個欄位（datetime,user_name,content）
    def get_pd_model(self):
        if self.datetime == '':
            return None
        else:
            return {'datetime': self.datetime,'user_name':self.user_name,'content':self.content}
    
    def get_db_model(self):
        if self.datetime == '':
            return None
        else:
            return {
              'ChatTime': self.datetime,
              'Content':  self.content,
              'UserName': self.user_name
            }
            
    
# In[set config]

#位置及檔名 file_path
# 輸入 
line_txt = './data/chat-2.txt'

# 輸出 
line_structure_output = 'line_structure_output_20180730修正版.xlsx'

# In[程式進入點 主程式]:

df = pd.DataFrame(columns=['datetime','user_name','content'])
with open(line_txt, 'r', encoding='utf-8') as f:
    #讀全部
    data = f.readlines()
    
    #一整天的記錄共用一個日期
    date = ''
    
    #句子種類 (1:日期,2:系統訊息,3:正常訊息)
    content_type = 0
    
    line_model = LineModel()
    
    con = db_connection()
    con.connect()
    for line in data:
        line= line.replace('\ufeff','')
        model = line.split('	')
       
        content_type = len(model)
        
        #儲存日期
        if is_date(model[0]):
            date = model[0]
            continue
        else:
            #不是日期 但長度只有1的話 屬於同一筆資料 (因為data是取換行符號 所以在句子中換行 還是屬於同一人發言 並且不做儲存的動作)
            if len(model) == 1:
                line_model.set_content(model[0])
       
        #開頭是時間 屬於新的一句話
        if(is_time(model[0])):
            #儲存句子
            df_obj = line_model.get_pd_model()
            db_obj = line_model.get_db_model()
            
            #第一次遇到時間 沒有上一句話 會是None 要排除
            if df_obj is not None:
                df = df.append(df_obj, ignore_index=True)
            
            #正常的一則訊息
            if content_type == 3:
                if is_time(model[0]):
                    line_model = LineModel()
                    line_model.set_line_model(date,model[0],model[1],model[2])
                    
            #系統訊息
            elif content_type == 2:
                    line_model = LineModel()
                    line_model.set_line_model(date,model[0],'system message',model[1])
                    
            #例外處理:例如句子中出現 '	' 這種用來區別的符號時 視為同個句子
            else:
                line_model.set_content(model[0]+model[1])
            
            
            
         
    con.close_connect() 
    #計算對話時間差
    '''
    df['time_distance'] = 0

    for time_distance in df['datetime'].items():
        index = time_distance[0]
        #到達最後一筆
        if index == df.index.max():
            break;

        this_time = datetime.strptime(str(df['datetime'][index]), "%Y-%m-%d %H:%M:%S")
        next_time = datetime.strptime(str(df['datetime'][index+1]), "%Y-%m-%d %H:%M:%S")
        df['time_distance'][index] = next_time - this_time
    '''
    #將最終分析結果寫入exce
    writer = pd.ExcelWriter(line_structure_output)
    df.to_excel(writer,'Sheet1')
    writer.close()
   