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
import sys
import os
import logging
import time

cwd = os.path.dirname(os.path.realpath(__file__))

filename = os.path.join(cwd, '{}.log'.format(datetime.date.today().isoformat()))
filenameold = os.path.join(cwd, '{}.log'.format((datetime.date.today() - datetime.timedelta(days = 3)).isoformat()))

logging.basicConfig(filename=filename,
                        filemode='a',
                        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S',
                        level=logging.INFO)
logger = logging.getLogger('tws')


class TwSender(object):
    def __init__(self):
        try:
            try:
                os.remove(filenameold)
            except BaseException:
                logger.error('Old log file not found')    
            logger.info('Loading keys...')
            keys = json.load(open(sys.path[0] + '/keyconf.json'))
            logger.info('Connecting to twitter api...')
            self.__api = twitter.Api(consumer_key = keys['consumer_key'],
                          consumer_secret = keys['consumer_secret'],
                          access_token_key = keys['access_token_key'],
                          access_token_secret = keys['access_token_secret'])
            logger.info('Loading users...')
            users = json.load(open(sys.path[0] + '/userconf.json'))
            self.__users = []
            for user in users:
                self.__users.append(User(user['user'], user['id']))
            logger.info('Updating users with empty last tweets...')
            self.__update_users_ids__()
            logger.info('SMTP server configuration...')
            self.__smtp_login__()
            logger.info('Collecting tweets...')
            self.__collect__()
            logger.info('Done!')
        except BaseException as err:
            logger.error('Cannot initialize! {}'.format(err))
        
    def __update_users_ids__(self):
        try:
            for user in self.__users:
                if user.user_id == '':
                    t = self.__api.GetUserTimeline(screen_name=user.name, count = 2)
                    if t[0].AsDict()['id'] < t[1].AsDict()['id']:
                        user.user_id = t[0].AsDict()['id']
                    else:
                        user.user_id = t[1].AsDict()['id']
            self.__flush_users__()
        except BaseException as err:
            logger.error('Failed to update users empty ids! {}'.format(err))
        
    def __flush_users__(self):
        try:
            with open(sys.path[0] + '/userconf.json', 'w') as fp:
                jdict = []
                for user in self.__users:
                    jdict.append({'user': user.name, 'id': user.user_id})
                json.dump(jdict, fp)
        except BaseException as err:
            logger.error('Cannot update userconf file! {}'.format(err))
    
    def __update_users__(self):
        try:
            nusers = []
            for user in self.__users:
    
                t = self.__api.GetUserTimeline(screen_name=user.name, since_id = user.user_id)
                idlist = []
                for s in t:
                    idlist.append(s.AsDict()['id'])
                if len(idlist) > 0:
                    ID = max(idlist)
                else:
                    ID = user.user_id
                nusers.append({'id':ID, 'user': user.name})
            self.__users = nusers
            self.__flush_users__()
        except BaseException as err:
            logger.error('Failed to update users ids! {}'.format(err))
            
    def __update_user__(self, user):
        try:    
            t = self.__api.GetUserTimeline(screen_name=user.name, since_id = user.user_id)
            idlist = []
            for s in t:
                idlist.append(s.AsDict()['id'])
            if len(idlist) > 0:
                ID = max(idlist)
            else:
                ID = user.user_id
            allbutone = [element for element in self.__users if element.name != user.name]
            
            allbutone.append(User(user.name, ID))
            self.__users = allbutone
            self.__flush_users__()
        except BaseException as err:
            logger.error('Failed to update user {}! {}'.format(user.name, err))
    
    def __collect__(self):
        try:
            for user in self.__users:
                t = self.__api.GetUserTimeline(screen_name=user.name, since_id = user.user_id)
                for s in t:
                    user.tweets.append(s)
        except BaseException as err:
            logger.error('Failed to collect tweets! {}'.format(err))
    
    def __smtp_login__(self):
        try:
            creds = json.load(open(sys.path[0] + '/smtpconf.json'))
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.connect("smtp.gmail.com", 587)
            server.ehlo()
            server.starttls()
            server.ehlo()
    
            #Next, log in to the server
            
            server.login(creds['log'], creds['pass'])
            self.__server = server
        except BaseException as err:
            logger.error('Failed to log in (smtp server)! {}'.format(err))

    def __send_email__(self, text, subject, fromaddr, toaddr_list, cc = []):
        try:
            for addr in toaddr_list:
                message = ("From: {}\r\n" .format(fromaddr)
                           + "To: {}\r\n".format(addr)
                           + "CC: {}\r\n".format(",".join(cc))
                           + "Subject: {}\r\n".format(subject)
                           + "{}\r\n".format(text))
    
                toaddrs = [addr] # + cc + bcc
                #Send the mail
                self.__server.sendmail(fromaddr, toaddrs, message)
        except BaseException as err:
            logger.error('Sending email failed! {}'.format(err))
    
    def __contains_non_ascii_characters__(self, str):
        return not all(ord(c) < 128 for c in str)
    
    def send(self, toaddr_list, skipreplies = True):
        try:
            if len(self.__users) == 0:
                logger.error('No users found, quitting')
                return
            logger.info('Sending tweets...')
            for user in self.__users:
                try:
                    if len(user.tweets) == 0:
                        logger.error('No tweets found for user {}'.format(user.name))
                        continue;
                    for s in user.tweets:
                        reply = False
                        retweet = False
                        d = datetime.datetime.strptime(s.AsDict()['created_at'], '%a %b %d %H:%M:%S +0000 %Y').date()
                        try:
                            if len(s.AsDict()['urls']) == 0:
                                if 'retweeted_status' in s.AsDict():
                                    retweet = True
                                    try:
                                        url_short = ''
                                        url_full = ''
                                        favs = ''
                                        
                                        
                                        if 'urls' in s.AsDict()['retweeted_status']:
                                            if len(s.AsDict()['retweeted_status']['urls']) > 0:
                                                if 'url' in s.AsDict()['retweeted_status']['urls'][0]:
                                                    url_short = s.AsDict()['retweeted_status']['urls'][0]['url']
                                                if 'expanded_url' in s.AsDict()['retweeted_status']['urls'][0]:
                                                    url_full = s.AsDict()['retweeted_status']['urls'][0]['expanded_url']
                                            else:
                                                if 'id' in s.AsDict()['retweeted_status']:
                                                    url_full = 'https://twitter.com/i/web/status/{}'.format(s.AsDict()['retweeted_status']['id'])
                                        if 'favorite_count' in s.AsDict()['retweeted_status']:
                                            favs = s.AsDict()['retweeted_status']['favorite_count']
                                    except BaseException as err:
                                        logger.error(err)
                                        url_short = ''
                                        url_full = '' 
                                        favs = ''
                                    
                                if 'in_reply_to_user_id' in s.AsDict() and not retweet:
                                    reply = True
                                    url_short = ''
                                    url_full = ''
                                    favs = ''
                                    if 'id' in s.AsDict():
                                        url_full = 'https://twitter.com/i/web/status/{}'.format(s.AsDict()['id'])
                                    if 'favorite_count' in s.AsDict():
                                            favs = s.AsDict()['favorite_count']
                                    if skipreplies:
                                        continue;
                            else:
                                url_short = ''
                                url_full = ''
                                favs = ''
                                if 'retweeted_status' in s.AsDict():
                                    retweet = True
                                if 'in_reply_to_user_id' in s.AsDict():
                                    reply = True
                                if 'urls' in s.AsDict():
                                    if len(s.AsDict()['urls']) > 0:
                                        if 'url' in s.AsDict()['urls'][0]:
                                            url_short = s.AsDict()['urls'][0]['url']
                                        if 'expanded_url' in s.AsDict()['urls'][0]:
                                            url_full = s.AsDict()['urls'][0]['expanded_url']
                                if 'favorite_count' in s.AsDict():
                                    favs = s.AsDict()['favorite_count']
                        except BaseException as err:
                            logger.error(err)
                            url_short = ''
                            url_full = ''
                            if 'id' in s.AsDict():
                                url_full = 'https://twitter.com/i/web/status/{}'.format(s.AsDict()['id'])                        
                            favs = ''
                        ttext = ''
                        if 'text' in s.AsDict():
                            ttext = s.AsDict()['text']
                        text = ("\r\n{}".format(ttext) 
                                + "\r\nCreated at: {}".format(d.strftime("%Y-%m-%d %H:%M:%S"))
                                + "\r\nTweet URL short: {}".format(url_short)
                                + "\r\nTweet URL full: {}".format(url_full) 
                                + "\r\nTweet favorites: {}".format(favs))
                        
                        if(self.__contains_non_ascii_characters__(text)):
                            plain_text = MIMEText(text.encode('utf-8'),'plain','utf-8') 
                        else:
                            plain_text = MIMEText(text,'plain')
                        if not reply and not retweet:
                            subject = '{} Tweets {}, {}'.format(s.AsDict()['user']['screen_name'], d.year, d.month)
                            logger.info('Sending tweet: {}'.format(subject))
                            self.__send_email__(text = plain_text, subject = subject, fromaddr = '', toaddr_list = toaddr_list)
                            time.sleep(10)
                        if retweet:
                            subject = '{} RETweets {}, {}'.format(s.AsDict()['user']['screen_name'], d.year, d.month)
                            logger.info('Sending retweet: {}'.format(subject))
                            self.__send_email__(text = plain_text, subject = subject, fromaddr = '', toaddr_list = toaddr_list)
                            time.sleep(10)
                        if not skipreplies and reply and not retweet:
                            subject = '{} Replies {}, {}'.format(s.AsDict()['user']['screen_name'], d.year, d.month)
                            logger.info('Sending reply: {}'.format(subject))
                            self.__send_email__(text = plain_text, subject = subject, fromaddr = '', toaddr_list = toaddr_list)
                            time.sleep(10)
                        self.__update_user__(user)
                except BaseException as err:
                    logger.error('Failed to send tweets for user: {}, {}'.format(user.name, err))
        except BaseException as err:
            logger.error('Cannot send! {}'.format(err))
            
    def cleanup(self):
        try:
            logger.info('Quitting SMTP server...')
            self.__server.quit()
            logger.info('Done!')
        except BaseException as err:
            logger.error('Cannot clean up! {}'.format(err))

class User(object):
    def __init__(self, name, user_id = ''):
        try:
            self.name = name
            self.user_id = user_id
            self.tweets = []
        except BaseException as err:
            logger.error('Cannot initialize user! {}'.format(err))
