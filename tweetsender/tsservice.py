# import the class
from tweetsender import TwSender
# create an instance, load configurations, collect tweets
tws = TwSender()
# send tweets and update userconf.json
tws.send(toaddr_list = ['some@email.com', 'another@email.com'])
# clean up after yourself
tws.cleanup()
