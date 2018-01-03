# tweetsender
Get tweets of particular users to your gmail inbox without using twitter app
So you can follow people you admire and read inspiring ideas without being annoyed with push notifications. Using the power of email, you can read tweets whenever you want and have all the tweets history in your inbox.

# Getting started
* Create an application in twitter with the help of their guide: https://developer.twitter.com/en/docs/basics/authentication/guides/access-tokens
* Place `tweetsender.py` along with `userconf.json`, `smtpconf.json` and `keyconf.json` in the same folder, say in `~/tweetsender`
* Edit `keyconf.json` and replace values with your actual keys retrieved in step 1
* Edit `smtpconf.json` and replace values with your actual login and pass from your gmail account
* Edit `userconf.json` and replace or add twitter users you wish to follow. You should replace id value by `""` (empty value) at first, then python script will manage it by itself
* Install dependencies if it is necessary
https://github.com/bear/python-twitter
```bash
pip install python-twitter
```
* Create an executable python3 script (say, `tsservice.py` as follows:
```python 3
# import the class
from tweetsender import TwSender
# create an instance, load configurations, collect tweets
tws = TwSender()
# send tweets and update userconf.json
tws.send(toaddr_list = ['some@email.com', 'another@email.com'])
# clean up after yourself
tws.cleanup()
```
and save it in the same directory (`~/tweetsender`).
* Check if script works (open your terminal and type):
```bash
python3 ~/tweetsender/tsservice.py
```
* Schedule the script via crontab (check every day in my case):
  * Open your terminal and type:
  ```bash
  crontab -e
  ```
  * Add the following line (you can change the freequency as you like it):
  ```bash
  0 6 * * * python3 /path/to/your/home/tweetsender/tsservice.py
  ```
  This will run the script every day at 6:00 am
