#!/usr/bin/python
import os
import time
import re
import rospy
from std_msgs.msg import String
from slackclient import SlackClient

MENTION_REGEX = '^<@(|[WU].+?)>(.*)'

RECOGNIZED_INTENT = '/recognized_intent'

class SlackRos():

    def __init__(self):
        self.slack_client = SlackClient(os.environ.get('SLACK_API_TOKEN'))

        # Default ros-channel
        self.channel_id = 'CATHE3NSJ'
        self.starterbot_id = None

        rospy.init_node('slack_ros')
        self.slack_to_ros = rospy.Publisher('slack_to_ros', String, queue_size=10)
        self.ros_to_slack = rospy.Subscriber('ros_to_slack', String, self.ros_slack_callback)

        self.speech = rospy.Subscriber('/speech', String, self.on_speech)
        self.intent = rospy.Publisher(RECOGNIZED_INTENT, String, queue_size=10)

        self.rate = rospy.Rate(10)
        self.spin()

    def spin(self):
        if self.slack_client.rtm_connect(with_team_state=False):
            print('Slack Bot running.')
            self.starterbot_id = self.slack_client.api_call('auth.test')['user_id']
            while not rospy.is_shutdown():
                command, channel = self.parse_bot_commands(self.slack_client.rtm_read())
                if command:
                    self.handle_command(command, channel)
                self.rate.sleep()
        else:
            print('Connection failed.')


    def ros_slack_callback(self, data):
        if self.channel_id is None:
            rospy.loginfo('No channel ID')
            pass
        else:
            self.slack_client.api_call('chat.postMessage',
                channel=self.channel_id,
                text=data.data)

    def parse_bot_commands(self, slack_events):
        for event in slack_events:
            if event['type'] == 'message' and not 'subtype' in event:
                user_id, message = self.parse_direct_mention(event['text'])
                if user_id == self.starterbot_id:
                    return message, event['channel']
        return None, None

    def parse_direct_mention(self, message_text):
        matches = re.search(MENTION_REGEX, message_text)
        return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

    def handle_command(self, command, channel):
        if command == 'start':
            self.channel_id = channel
            response = 'You reset my current channel.'
        else:
            self.intent.publish(String(command))

        self.slack_client.api_call(
            'chat.postMessage',
            channel=channel,
            text=response
        )
    
    def on_speech(self, data):
        response = '*** DIALOGFLOW ***: ' + data.data
        self.slack_client.api_call(
            'chat.postMessage',
            channel=self.channel_id,
            text=response
        )

if __name__ == '__main__':
    try:
        slack_ros = SlackRos()
    except rospy.ROSInterruptException:
            pass
