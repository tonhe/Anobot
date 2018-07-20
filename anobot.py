import os
import sys
import time
import logging
from slackclient import SlackClient

# This token should be a legacy user token from an admin
# https://api.slack.com/custom-integrations/legacy-tokens
API_TOKEN = 'xoxp-0000000000000000000'
# Channels to remove messages from non-admins
MONITORED_CHANNELS = ['announcements']
# Slack group empowering users to post in above channel
EMPOWERED_USERS_GROUP = 'AnnouncementsUsers'

# Logging Config
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
# logger.setLevel(logging.DEBUG)  # Uncomment to set logging to DEBUG


def parse_bot_commands(sc):
    slack_events = sc.rtm_read()
    for event in slack_events:
        if event['type'] == 'message':
            logger.debug(event)
            try:
                if event['hidden'] is True:
                    continue  # Don't try to delete hidden messages
            except Exception:
                pass  # Just in case....
            chan, msg_id = event['channel'], event['ts']
            chan_info = sc.api_call("channels.info", channel=chan)
            if chan_info['channel']['name'] not in MONITORED_CHANNELS:
                continue  # Skip messages from non-monitored channels
            try:
                user_id = event['user']
            except Exception:  # This deletes channel joins / leaves
                logger.debug(sc.api_call("chat.delete", channel=chan, ts=msg_id, as_user=True))
            else:
                groups = sc.api_call("usergroups.list")['usergroups']
                for group in groups:
                    id, name = group['id'], group['name']
                    if name == EMPOWERED_USERS_GROUP:
                        em_users = sc.api_call("usergroups.users.list", usergroup=id)['users']
                user_info = sc.api_call("users.info", user=user_id)['user']
                if user_info['id'] in em_users:
                    continue  # User is in the EMPOWERED_USERS_GROUP
                elif True in (user_info['is_admin'],
                              user_info['is_owner'],
                              user_info['is_primary_owner']):
                    continue  # User is Admin/owner
                else:  # User isn't allowed to post, deleting the message
                    logger.debug(sc.api_call("chat.delete", channel=chan, ts=msg_id, as_user=True))


if __name__ == "__main__":
    fpid = os.fork()
    if fpid != 0:
        sys.exit(0)  # Running as daemon now. PID is fpid
    client = SlackClient(API_TOKEN)
    if client.rtm_connect():
        logger.debug("Successfull Connection! - Listening for events.")
        while True:
            parse_bot_commands(client)
            time.sleep(1)
    else:
        logger.debug("Connection Failed.....")
