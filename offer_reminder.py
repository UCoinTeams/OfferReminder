#-*- coding:utf-8 -*-
import time
import logging
import telebot
from apscheduler.schedulers.blocking import BlockingScheduler
from requests import session, cookies
from lxml import etree
# from retrying import retry

logging.getLogger().setLevel(logging.ERROR)
logging.basicConfig(
    format='%(asctime)s %(message)s',
    handlers=[
        logging.FileHandler("run.log", encoding="UTF-8"),
        logging.StreamHandler(),
    ],
)

## u2 cookies
nexusphp_u2 = ''
# __cfduid = ''

## tg bot
tg_bot_api = ''
tg_channel_id = ''
tg_group_id = ''

bot = telebot.TeleBot(tg_bot_api)

# @retry()
def get_last_promotion_id():
    url = 'https://u2.dmhy.org/promotion.php'
    logging.info('[I] get_last_promotion_id: 发起请求')
    result = session.get(url)
    # print(result.text)
    html = etree.HTML(result.text.encode('utf-8'))
    table = html.xpath('//h2[text()=\'优惠历史\']/following::table[1]//table')[0]
    promotion_id = int(table.xpath('.//a[@class=\'faqlink\']/text()')[0])
    # promotion_id = 433966
    return promotion_id

# @retry()
def get_promotion_info(promotion_id):
    promotion_url = 'https://u2.dmhy.org/promotion.php?action=detail&id='+str(promotion_id)
    result = session.get(promotion_url)
    html = etree.HTML(result.text.encode('utf-8'))
    content = html.xpath('//h2[text()=\'优惠详细信息\']/following::table[2]')[0]
    effective_seed = content.xpath('.//td[text()=\'有效种子\']/following::td[1]//text()')[0]
    logging.info(f'[I] 种子: {effective_seed}')
    if effective_seed == '种子不存在或无效，无法设置。':
        return None
    elif effective_seed != '全局':
        effective_seed_url = content.xpath('.//td[text()=\'有效种子\']/following::td[1]//a/@href')[0]
        allseed = 'no'
    else:
        effective_seed_url = 'torrents.php'
        allseed = 'yes'
    try:
        effective_user = content.xpath('.//td[text()=\'有效用户\']/following::td[1]//text()')[0]
    except:
        effective_user = ''
    creater = content.xpath('.//td[text()=\'创建\']/following::*[1]//text()')[0]
    fromtime = content.xpath('.//td[text()=\'自\']/following::*[1]//text()')[0]
    term = ''.join(content.xpath('.//td[text()=\'期限\']/following::td[1]//text()'))
    ratio = content.xpath('.//td[text()=\'比率\']/following::td[1]/img/@alt')[0]
    if ratio == 'Promotion':
        ratio = ''
        try:
            up_ratio = content.xpath('.//img[@alt=\'上传比率\']/following::*[1]//text()')[0]
            ratio = '上传比率 ' + up_ratio.lower()
        except:
            pass
        try:
            down_ratio = content.xpath('.//img[@alt=\'下载比率\']/following::*[1]//text()')[0]
            ratio += (' ' if ratio != '' else '') + '下载比率 ' + down_ratio.lower()
        except:
            pass
    elif ratio == '2X':
        ratio = ' 👆2.00x👇1.00x'
    elif ratio == 'FREE':
        ratio = ' Free'
    elif ratio == '2X 50%':
        ratio = ' 👆2.00x👇0.50x'
    elif ratio == '30%':
        ratio = ' 👆1.00x👇0.30x'
    elif ratio == '50%':
        ratio = ' 👆1.00x👇0.50x'
    if content.xpath('.//td[text()=\'备注\']/following::td[1]//fieldset') == []:
        remark = content.xpath('.//td[text()=\'备注\']/following::td[1]/span//text()')[0]
    else:
        remark = content.xpath('.//td[text()=\'备注\']/following::td[1]//legend')[0].tail
        if remark == None:
            remark = ''
    state = content.xpath('.//td[text()=\'状态\']/following::td[1]//text()')[0]

    promotion_info = {'promotion_id': promotion_id,
                      'effective_seed': effective_seed,
                      'effective_user': effective_user,
                      'effective_seed_url': effective_seed_url,
                      'creater': creater,
                      'fromtime': fromtime.replace('\xad', '').replace('\u00ad', ''),
                      'term': term,
                      'ratio': ratio,
                      'remark': remark,
                      'allseed': allseed,
                      'state': state}
    return promotion_info

# @retry()
def send_tg_msg(promotion_info):
    """处理数据推送到 Telegram """
    # doc: https://core.telegram.org/bots/api#markdownv2-style
    if promotion_info['allseed'] == 'no': # 不是全局优惠
        promotion_info["term"] = promotion_info["term"].replace("小时", " Hours").replace("(", "\n\\(").replace(")", " GMT\\+8\\)").replace("-", "\\-")
        promotion_info["state"] = promotion_info["state"].replace("有效", "有效\\-Effective\\-有効").replace("未生效", "*未生效\\-Ineffective\\-無効*")
        text = (
            f'\\[\\#优惠提醒 [{promotion_info["promotion_id"]}](https://u2.dmhy.org/promotion.php?action=detail&id={promotion_info["promotion_id"]})\\]\n'
            '*种子\\|Torrent\\|トレント:*\n'
            f'[{parse_markdown_v2(promotion_info["effective_seed"].replace("全局","全局 all"))}](https://u2.dmhy.org/{promotion_info["effective_seed_url"]})\n\n'

            f'*类型\\|Type\\|種類:* `{promotion_info["ratio"].replace("上传比率","👆").replace("下载比率","👇")}`\n'
            f' `{promotion_info["term"]}`\n'
            '*状态\\|State\\|状態: *\n'
            f' {promotion_info["state"]}\n\n'
        )
        bot.send_message(chat_id=tg_channel_id, text=text, parse_mode='MarkdownV2')
    elif promotion_info['allseed'] == 'yes': # 全局优惠
        promotion_info["term"] = promotion_info["term"].replace("小时", " Hours").replace("(", "\n\\(").replace(")", " GMT\\+8\\)").replace("-", "\\-")
        text = (
            f"\\[\\#优惠提醒 [{promotion_info['promotion_id']}](https://u2.dmhy.org/promotion.php?action=detail&id={promotion_info['promotion_id']})\\]\n"
            f"*优惠类型: *全站 {promotion_info['ratio'].replace('上传比率','👆').replace('下载比率','👇')}\n"
            f"*有效时间: *`{promotion_info['term']}`\n"
            f"*当前状态: *{promotion_info['state'].replace('有效', '有效').replace('未生效', '*未生效*')} 至 {promotion_info['fromtime']}\n\n"

            f"\\[\\#Promotion [{promotion_info['promotion_id']}](https://u2.dmhy.org/promotion.php?action=detail&id={promotion_info['promotion_id']})\\]\n"
            f"*Promotion type: *{promotion_info['ratio'].replace('上传比率','👆').replace('下载比率','👇')} for all torrents\n"
            f"*Time limit: *`{promotion_info['term']}`\n"
            f"*Current Status: *{promotion_info['state'].replace('有效', 'Effective').replace('未生效', '*In future*')}\n\n"

            f"\\[\\#プロモーション [{promotion_info['promotion_id']}](https://u2.dmhy.org/promotion.php?action=detail&id={promotion_info['promotion_id']})\\]\n"
            f"*プロモーションの種類: *すべてのトレント{promotion_info['ratio'].replace('上传比率','👆').replace('下载比率','👇')}\n"
            f"*有効時間: *`{promotion_info['term']}`\n"
            f"*現在の状態: *{promotion_info['state'].replace('有效', '有効').replace('未生效', '*現在無効*')}\n\n"
        )
        c_msg = bot.send_message(chat_id=tg_channel_id, text=text, parse_mode='MarkdownV2')
        g_msg = bot.send_message(chat_id=tg_group_id, text=text, parse_mode='MarkdownV2')
        if promotion_info['state'] == '未生效':
            pin_disable_notification = True
        elif promotion_info['state'] == '有效':
            pin_disable_notification = False
        bot.pin_chat_message(chat_id=tg_group_id, message_id=g_msg.message_id, disable_notification=pin_disable_notification)
        bot.pin_chat_message(chat_id=tg_channel_id, message_id=c_msg.message_id, disable_notification=pin_disable_notification)


headers={'Connection':'keep-alive',
         'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.100 Safari/437.36',
         'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
         'Accept-Language':'zh-CN,zh;q=0.8'}

def parse_markdown_v2(text: str) -> str:
    """markdown_v2 转译"""
    return text.translate(
        str.maketrans(
            {
                '_': '\\_',
                '*': '\\*',
                '[': '\\[',
                ']': '\\]',
                '(': '\\(',
                ')': '\\)',
                '~': '\\~',
                '`': '\\`',
                '>': '\\>',
                '#': '\\#',
                '+': '\\+',
                '-': '\\-',
                '=': '\\=',
                '|': '\\|',
                '{': '\\{',
                '}': '\\}',
                '.': '\\.',
                '!': '\\!',
            }
        )
    )

session = session()
session.headers.clear()
session.headers.update(headers)
cookie_jar = cookies.RequestsCookieJar()
cookie_jar.set("nexusphp_u2", nexusphp_u2, domain="u2.dmhy.org")
# cookie_jar.set("__cfduid", __cfduid, domain=".dmhy.org")
session.cookies = cookie_jar
promotion_id = 0

def offer_checker():
    global promotion_id
    logging.info('\n[I] 本次运行：' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    try:
        new_promotion_id = get_last_promotion_id()
    except IndexError:
        logging.error('[E] 未能获取到合法的内容：U2娘可能宕机')
        return 1
    logging.info(f'[I] 最近一次魔法: {new_promotion_id}')
    if promotion_id == 0:
        promotion_id = new_promotion_id
        logging.info(f'[I] 初始化魔法 ID：{promotion_id}')
    elif promotion_id > new_promotion_id:
        logging.warning(f'[E] 错误的魔法：当前：{promotion_id}；获取：{new_promotion_id}')
        return 0
    logging.info(f'[I] 处理期间新魔法队列：{promotion_id} ~ {new_promotion_id}')
    for i in range(promotion_id, new_promotion_id+1):
        logging.info(f'[I] 处理魔法：{i}')
        promotion_info = get_promotion_info(i)
        if promotion_info:
            logging.info(f'[I] 成功获取了魔法信息：{i}')
            if promotion_info['effective_user'] == '所有人':
                logging.info('[I] 推送魔法：', promotion_info)
                try:
                    send_tg_msg(promotion_info)
                except Exception as e:
                    logging.error(f'[E] 推送魔法失败：{e} \n{promotion_info}')
                    return 1
        else:
            logging.error(f'[E] 异常魔法信息：{i}')
            return 1
    promotion_id = new_promotion_id + 1
    logging.info('[I] 本次任务处理完毕')


def main():
    logging.info('[I] 已启动')
    offer_checker()
    scheduler = BlockingScheduler(timezone='Asia/Shanghai')
    scheduler.add_job(
        func=offer_checker,
        trigger='interval',
        minutes=1
    )
    logging.info('\n[I] 定时任务已设置')
    scheduler.start()

    
if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        exit()