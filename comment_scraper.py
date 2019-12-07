import pandas as pd
import numpy as np
import time
import webbrowser
import re

import vk

import warnings
warnings.filterwarnings('ignore')

class LoginExeption(Exception):
    pass
    
class GetCommentsFromGroup:
    def __init__(self, api, group, num_posts, num_comments, need_thread=True):
        self.api = api
        self.group = group
        self.group_id = 0
        self.num_posts = num_posts
        self.num_comments = num_comments
        self.id_list = None
        self.num_threads = 10 if need_thread else 0
        self.post_texts = {}
    
    def _attachment_and_url(self, list_of_attachments):
        if list_of_attachments is np.nan:
            return np.nan
        attachment_types = []
        for attachment in list_of_attachments:
            attachment_types.append(attachment['type'])        
        return attachment_types

    def _get_id_posts(self):
        id_list = []
        offset = 0        
        # we should devide into n groups with less than 100 items
        num_of_groups100 = self.num_posts // 100
        
        # getting id`s
        for i in range(num_of_groups100):
            time.sleep(0.3)
            x = self.api.wall.get(domain=self.group,
                             count=100, 
                             offset=offset)
            offset += 100
            for j in range(len(x['items'])):
                id_cur = x['items'][j]['id']
                id_list.append(id_cur)
                self.post_texts[id_cur] = x['items'][j]['text']
                
        # get id of other posts
        num_of_not_group100 = self.num_posts % 100
        if num_of_not_group100 != 0:
            time.sleep(0.3)
            x = self.api.wall.get(domain=self.group,
                                 count=self.num_posts % 100,
                                 offset=offset)
            for j in range(len(x['items'])):
                id_cur = x['items'][j]['id']
                id_list.append(id_cur)
                self.post_texts[id_cur] = x['items'][j]['text']
        self.group_id = x['items'][0]['owner_id']
        self.id_list = pd.Series(id_list)
        return self.id_list
    
    def _get_comments_post_by_id(self, id_post):
        if self.id_list is None:
            self._get_id_posts()
        time.sleep(0.3)
        request = self.api.wall.getComments(owner_id=self.group_id,
                               post_id=id_post,
                               need_likes=1,
                               count=120,
                               thread_items_count=10,
                               sort='asc')
        comments_to_get = min(self.num_comments, request['count'])
        groups100 = comments_to_get // 100
        not_group100 = comments_to_get % 100
        res = request['items']
        if groups100 == 0:
            return pd.DataFrame(res)
        for num_group in range(1, groups100):
            time.sleep(0.3)
            res += self.api.wall.getComments(owner_id=self.group_id,
                                            post_id=id_post,
                                            need_likes=1,
                                            count=100,
                                            thread_items_count=10,
                                            offset=100*num_group,
                                            sort='asc')['items']
        if not_group100 == 0:
            return pd.DataFrame(res)
        time.sleep(0.3)
        res += self.api.wall.getComments(owner_id=self.group_id,
                                            post_id=id_post,
                                            need_likes=1,
                                            count=not_group100,
                                            thread_items_count=10,
                                            offset=100*groups100,
                                            sort='asc')['items']
        return pd.DataFrame(res)
    
    def _get_comments_not_format_slow(self):
        if self.id_list is None:
            self._get_id_posts()
        return pd.concat([self._get_comments_post_by_id(id_post) for id_post in self.id_list], ignore_index=True)
   
    
    def get_comments(self):
        df = self._get_comments_not_format_slow()
        if self.num_threads > 0:
            threads = []
            for comment_thread in df.thread.dropna():
                threads += comment_thread['items']
        df = pd.concat([df, pd.DataFrame(threads)],
                         ignore_index=True, sort=False).drop('thread', axis=1)
        df['likes'] = df['likes'].map(lambda x: 0 if x is np.nan else x['count'])
        if 'attachment' in df.columns:
            df['attachments'] = df['attachments'].map(self._attachment_and_url)
        df['owner_id'] = [self.group] * len(df)
        df['post_text'] = df['post_id'].map(lambda x: self.post_texts.get(x))
        df.rename(columns={'owner_id': 'group',
                  'id': 'id_comment', 'from_id': 'id_user'}, inplace=True)
        return df
        
        
        
class CreateAPI:
    def __init__(self):
        self.api = None
    
    def create_using_login_password(self, login, password):
        session = vk.AuthSession('7235023', login, password, scope='wall, groups')
        self.api = vk.API(session, v='5.103')
        return self.api
    
    def get_tocken(self):
        url = 'https://oauth.vk.com/authorize?client_id=7235023&scope=groups,wall&redirect_uri=https://oauth.vk.com/blank.html&display=page&v=5.21&response_type=token'
        webbrowser.open(url, new=2)
        print('Copy address from site that opened, call method create_using_tocken with parameter - str with copied address')
    
    def create_using_tocken(self, url_tocken):
        regexp_find = re.findall(re.compile(r'access_token=(.*)&e.*&user_id=(.*)'), url_tocken)
        tocken = regexp_find[0][0]
        user_id = regexp_find[0][1]
        session = vk.Session(access_token=tocken)
        self.api = vk.API(session, v='5.103')
        return self.api
    
    def get_created_api(self):
        if self.api is None:
            raise LoginExeption('Before get api you should create api.')
        return self.api
            
    def test_API(self):
        if self.api is None:
            raise LoginExeption('Before test api you should create api.')
        vk_api.wall.post(message='hello')
        
        
        
class GetInformationFromVk:
    def __init__(self, api):
        self.api = api
    
    def get_comments(self, domains,  
                 number_of_posts=10, number_of_coments_in_post=20, with_thread=True):
        res = []
        for domain in domains:
            getter = GetCommentsFromGroup(self.api, domain,
                                          number_of_posts,
                                          number_of_coments_in_post,
                                          with_thread)
            res.append(getter.get_comments())
        return pd.concat(res, ignore_index=True)