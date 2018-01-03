# -*- coding: utf-8 -*-
"""
Created on Thu Dec 28 22:52:36 2017

@author: nurtdinovadf
"""

import twitter
import json
import smtplib
import datetime
from email.mime.text import MIMEText

class TwSender(object):
    def __init__(self):
        print('[INFO] Loading keys...')
        keys = json.load(open('keyconf.json'))
        print('[INFO] Connecting to twitter api...')
        self.__api = twitter.Api(consumer_key = keys['consumer_key'],
                      consumer_secret = keys['consumer_secret'],
                      access_token_key = keys['access_token_key'],
                      access_token_secret = keys['access_token_secret'])
        print('[INFO] Loading users...')
        self.__users = json.load(open('userconf.json'))
        print('[INFO] Updating users with empty last tweets...')
        self.__update_users_ids__()
        print('[INFO] SMTP server configuration...')
        self.__smtp_login__()
        print('[INFO] Collecting tweets...')
        self.__collect__()
        print('[INFO] Done!')
        
    def __update_users_ids__(self):
        for user in self.__users:
            if user['id'] == '':
                t = self.__api.GetUserTimeline(screen_name=user['user'], count = 2)
                if t[0].AsDict()['id'] < t[1].AsDict()['id']:
                    user['id'] = t[0].AsDict()['id']
                else:
                    user['id'] = t[1].AsDict()['id']
        self.__flush_users__(self.__users)
        
    def __flush_users__(self, users):
        with open('userconf.json', 'w') as fp:
            json.dump(users, fp)
    
    def __update_users__(self):
        nusers = []
        for user in self.__users:

            t = self.__api.GetUserTimeline(screen_name=user['user'], since_id = user['id'])
            idlist = []
            for s in t:
                idlist.append(s.AsDict()['id'])
            ID = max(idlist)
            nusers.append({'id':ID, 'user': user['user']})
        self.__users = nusers
        self.__flush_users__(nusers)
    
    def __collect__(self):
        ts = []
        for user in self.__users:
            t = self.__api.GetUserTimeline(screen_name=user['user'], since_id = user['id'])
            for s in t:
                ts.append(s)
        self.tweets_to_send = ts
    
    def __smtp_login__(self):
        creds = json.load(open('smtpconf.json'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.connect("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.ehlo()

        #Next, log in to the server
        
        server.login(creds['log'], creds['pass'])
        self.__server = server

    def __send_email__(self, text, subject, fromaddr, toaddr_list, cc = []):

        for addr in toaddr_list:
            message = ("From: {}\r\n" .format(fromaddr)
                       + "To: {}\r\n".format(addr)
                       + "CC: {}\r\n".format(",".join(cc))
                       + "Subject: {}\r\n".format(subject)
                       + "{}\r\n".format(text))

            toaddrs = [addr] # + cc + bcc
            #Send the mail
            self.__server.sendmail(fromaddr, toaddrs, message)
    
    def __contains_non_ascii_characters__(self, str):
        return not all(ord(c) < 128 for c in str)
    
    def send(self, toaddr_list):
        if len(self.tweets_to_send) == 0:
            print('[INFO] No new tweets found, quitting')
            return
        print('[INFO] Sending tweets...')
        for s in self.tweets_to_send:
            d = datetime.datetime.strptime(s.AsDict()['created_at'], '%a %b %d %H:%M:%S +0000 %Y').date()
            try:
                if len(s.AsDict()['urls']) == 0:
                    if 'retweeted_status' in s.AsDict():
                        url_short = s.AsDict()['retweeted_status']['urls'][0]['url']
                        url_full = s.AsDict()['retweeted_status']['urls'][0]['expanded_url']
                        favs = s.AsDict()['retweeted_status']['favorite_count']
                    if 'in_reply_to_user_id' in s.AsDict():
                        url_short = ''
                        url_full = 'https://twitter.com/i/web/status/{}'.format(s.AsDict()['id'])
                        favs = s.AsDict()['favorite_count']
                    else:
                        url_short = ''
                        url_full = ''
                        favs = ''
                else:
                    url_short = s.AsDict()['urls'][0]['url']
                    url_full = s.AsDict()['urls'][0]['expanded_url']
                    favs = s.AsDict()['favorite_count']
            except BaseException:
                url_short = ''
                url_full = 'https://twitter.com/i/web/status/{}'.format(s.AsDict()['id'])
                favs = ''
            text = ("\r\n{}".format(s.AsDict()['text']) 
                    + "\r\nCreated at: {}".format(d.strftime("%Y-%m-%d %H:%M:%S"))
                    + "\r\nTweet URL short: {}".format(url_short)
                    + "\r\nTweet URL full: {}".format(url_full) 
                    + "\r\nTweet favorites: {}".format(favs))
            
            if(self.__contains_non_ascii_characters__(text)):
                plain_text = MIMEText(text.encode('utf-8'),'plain','utf-8') 
            else:
                plain_text = MIMEText(text,'plain')
            subject = '{} Tweets {}, {}'.format(s.AsDict()['user']['screen_name'], d.year, d.month)
            print('[INFO] Sending tweet: {}'.format(subject))
            self.__send_email__(text = plain_text, subject = subject, fromaddr = '', toaddr_list = toaddr_list)
        print('[INFO] Updating users` last tweets')
        self.__update_users__()
        print('[INFO] Done!')
            
    def cleanup(self):
        print('[INFO] Quitting SMTP server...')
        self.__server.quit()
        print('[INFO] Done!')
