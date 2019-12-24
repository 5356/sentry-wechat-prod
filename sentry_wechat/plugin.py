"""
sentry_wechat.models
~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2019 by Jerry hu, see AUTHORS for more details.
:license: BSD, see LICENSE for more details.
"""

import json

import requests
from sentry.plugins.bases.notify import NotificationPlugin
from django import forms

import sentry_wechat

def validate_urls(value, **kwargs):
    output = []
    for url in value.split('\n'):
        url = url.strip()
        if not url:
            continue
        if not url.startswith(('http://', 'https://')):
            raise PluginError('Not a valid URL.')
        if not is_valid_url(url):
            raise PluginError('Not a valid URL.')
        output.append(url)
    return '\n'.join(output)

# https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=4929eab2-xxxx
class WechatForm(NotificationPlugin):
    urls = forms.CharField(
        label=_('Wechat robot url'),
        widget=forms.Textarea(attrs={
            'class': 'span6', 'placeholder': 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=4929eab2'}),
        help_text=_('Enter Wechat robot url.'))

    def clean_url(self):
        value = self.cleaned_data.get('url')
        return validate_urls(value)

 
class WechatPlugin(NotificationPlugin):
    """
    Sentry plugin to send error counts to Wechat.
    """
    author = 'jerry hu'
    author_url = 'https://github.com/jerryhu1234/sentry-wechat'
    version = sentry_wechat.VERSION
    description = "Integrates wechat robot."
    resource_links = [
        ('Bug Tracker', 'https://github.com/jerryhu1234/sentry-wechat/issues'),
        ('Source', 'https://github.com/jerryhu1234/sentry-wechat'),
        ('README', 'https://github.com/jerryhu1234/sentry-wechat/blob/master/README.md'),
    ]

    slug = 'Wechat'
    title = 'Wechat'
    conf_title = title
    conf_key = slug

    project_conf_form = WechatForm
    timeout = getattr(settings, 'SENTRY_WECHAT_TIMEOUT', 3)
    logger = logging.getLogger('sentry.plugins.wechat')

    # def is_configured(self, project, **kwargs):
    #     return bool(self.get_option('urls', project))

    def is_configured(self, project):
        """
        Check if plugin is configured.
        """
        return bool(self.get_option('urls', project))

    def get_webhook_urls(self, project):
        url = self.get_option('urls', project)
        if not url:
            return ''
        return url 

    def send_webhook(self, url, payload):
        return safe_urlopen(
            url=url,
            json=payload,
            timeout=self.timeout,
            verify_ssl=False,
        )

    def get_group_url(self, group):
        return absolute_uri(reverse('sentry-group', args=[
            group.team.slug,
            group.project.slug,
            group.id,
        ]))


    def notify_users(self, group, event, *args, **kwargs):
        self.post_process(group, event, *args, **kwargs)

    def post_process(self, group, event, *args, **kwargs):
        """
        Process error.
        """
        if not self.is_configured(group.project):
            return

        if group.is_ignored():
            return

        url = self.get_webhook_urls('url', group.project)
        title = u"New alert from {}".format(event.project.slug)
# {
#     "msgtype": "markdown",
#     "markdown": {
#         "content": "实时新增用户反馈<font color=\"warning\">132例</font>，请相关同事注意。\n
#          >类型:<font color=\"comment\">用户反馈</font> \n
#          >普通用户反馈:<font color=\"comment\">117例</font> \n
#          >VIP用户反馈:<font color=\"comment\">15例</font>"
#     }
# }
        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": u"#### {title} \n > {message} [href]({url})".format(
                    title=title,
                    message=event.message,
                    url=u"{}events/{}/".format(group.get_absolute_url(), event.id),
                )
            }
        }
        requests.post(
            url=url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(data).encode("utf-8")
        )