from thrift.transport.THttpClient import THttpClient
from thrift.protocol.TCompactProtocol import TCompactProtocol
from boteater_lib import BoteaterService
from boteater_lib.ttypes import *
import json, re, ast, traceback, datetime, copy, os, base64, requests, tempfile, time, shutil, urllib, string, random, ntpath
from random import randint


class Boteater():
    def __init__(self, my_app, my_token=None):
        self.lineServer = "https://ga2.line.naver.jp"
        self.lineOBS = "https://obs-sg.line-apps.com"
        self.boteaterApi = "https://api.boteater.us"
        self.liffServer = "https://api.line.me/message/v3/share"
        self.stickerLink = "https://stickershop.line-scdn.net/stickershop/v1/sticker/{}/iPhone/sticker@2x.png"
        self.stickerLinkAnimation = "https://stickershop.line-scdn.net/stickershop/v1/sticker/{}/iPhone/sticker_animation@2x.png"
        self.dataHeaders = self.readJson("headers.json")
        if my_app in self.dataHeaders:
            self.headers = self.dataHeaders[my_app]
            if my_token != None:
                self.headers["X-Line-Access"] = my_token
            else:
                del self.headers["X-Line-Access"]
                self.headers["X-Line-Access"] = self.qrLogin(self.headers)
                #self.headers["X-Line-Access"] = self.qrLoginRotate("ios_ipad")
        else:
            raise Exception('APP not found!!!')

        ### CONNECT TO POOL ###
        transport = THttpClient(self.lineServer + '/P4')
        transport.setCustomHeaders(self.headers)
        transport.open()
        protocol = TCompactProtocol(transport)
        self.pool = BoteaterService.Client(protocol)
        
        ### CONNECT TO TALK ###
        transport = THttpClient(self.lineServer + '/api/v4/TalkService.do')
        transport.setCustomHeaders(self.headers)
        transport.open()
        protocol = TCompactProtocol(transport)
        self.talk = BoteaterService.Client(protocol)

        ### CONNECT TO CHANNEL ###
        transport = THttpClient(self.lineServer + '/CH4')
        transport.setCustomHeaders(self.headers)
        transport.open()
        protocol = TCompactProtocol(transport)
        self.channel = BoteaterService.Client(protocol)

        ### CONNECT TO CALL ###
        transport = THttpClient(self.lineServer + '/V4')
        transport.setCustomHeaders(self.headers)
        transport.open()
        protocol = TCompactProtocol(transport)
        self.call = BoteaterService.Client(protocol)

        ### CONNECT TO SHOP ###
        transport = THttpClient(self.lineServer + '/TSHOP4')
        transport.setCustomHeaders(self.headers)
        transport.open()
        protocol = TCompactProtocol(transport)
        self.shop = BoteaterService.Client(protocol)

        ### CONNECT TO LIFF ###
        transport = THttpClient(self.lineServer + '/LIFF1')
        transport.setCustomHeaders(self.headers)
        transport.open()
        protocol = TCompactProtocol(transport)
        self.liff = BoteaterService.Client(protocol)

        self.profile = self.getProfile()
        self.lastOP = self.getLastOpRevision()
        self.liffPermision()
        self.tokenOBS = self.acquireEncryptedAccessToken()
        print("[ Login ] Display Name: " + self.profile.displayName)

        ### TIMELINE HEADERS ###
        self.tl_headers= copy.deepcopy(self.headers)
        self.tl_headers["X-Line-ChannelToken"] = self.issueChannelToken('1341209950').channelAccessToken
        self.tl_headers["X-Line-Mid"] = self.profile.mid
        self.tl_headers["X-Line-AcceptLanguage"] = 'en'
        self.tl_headers["X-Requested-With"] = 'jp.naver.line.android.LineApplication'
        self.tl_headers["Content-Type"] = 'application/json'




    ### OBJECT FUNCTION ###

    def readJson(self, filename):
        with open(filename) as f:
            try:
                data = json.loads(f)
            except:
                data = json.load(f)
            f.close()
        return data

    def writeJson(self, filename, data):
        with open(filename, "w") as f:
            json.dump(data,f,indent=4,sort_keys=True)
            f.close()
        return

    def object2Direct(self, url, ext, headers=False):
        data = {"url": url,
                "ext": ext}
        if headers == False:
            r = requests.post(self.boteaterApi + "/local_drive", data=data)
            return json.loads(r.text)["result"]
        if headers == True:
            r = requests.post(self.boteaterApi + "/local_drive", data=data, headers=self.headers)
            return json.loads(r.text)["result"]

    def object2Gdrive(self, url, ext, headers=False):
        data = {"url": url,
                "ext": ext}
        if headers == False:
            r = requests.post(self.boteaterApi + "/google_drive", data=data)
            return json.loads(r.text)["result"]
        if headers == True:
            r = requests.post(self.boteaterApi + "/google_drive", data=data, headers=self.headers)
            return json.loads(r.text)["result"]

    def downloadObjectMsg(self, messageId):
        path = self.genTempFile()
        r = requests.get(self.lineOBS+"/talk/m/download.nhn?oid="+messageId, headers=self.headers, stream=True)
        if r.status_code == 200:
            with open(path, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
                f.close()
            return path
        else:
            raise Exception('[ Error ] Download object')

    def uploadObjTalk(self, path, type='image', objId=None, to=None):
        headers = copy.deepcopy(self.headers)
        if type == 'image' or type == 'video' or type == 'audio' or type == 'file':
            link = self.lineOBS + '/talk/m/upload.nhn'
            files = {'file': open(path, 'rb')}
            data = {'params': json.dumps({'oid': objId,'size': len(open(path, 'rb').read()),'type': type})}
        elif type == 'gif':
            link = self.lineOBS + '/r/talk/m/reqseq'
            files = None
            data = open(path, 'rb').read()
            params = {
                'oid': 'reqseq',
                'reqseq': '%s' % str(self.lastOP),
                'tomid': '%s' % str(to),
                'size': '%s' % str(len(data)),
                'range': len(data),
                'type': 'image'
            }
            headers['Content-Type'] = 'image/gif',
            headers['Content-Length'] = str(len(data)),
            headers['x-obs-params']= self.genOBSParams(params)
        r = self.server.postContent(link, data=data, headers=headers, files=files)
        if r.status_code != 201:
            raise Exception('[ Error ] Upload object' )
        return objId


    def genRandom(self, count):
        random.seed = (os.urandom(1024))
        return ''.join(random.choice(string.ascii_letters + string.digits) for i in range(count))

    def genTempFile(self):
        name, path = 'tmpfile-%s-%i.bin' % (int(time.time()), randint(0, 9)), tempfile.gettempdir()
        return os.path.join(path, name)

    def genOBSParams(self, params):
        return base64.b64encode(json.dumps(params).encode('utf-8'))

    def genObjectId(self):
        random.seed = (os.urandom(1024))
        return ''.join(random.choice("abcdef1234567890") for i in range(32))



    ### LIFF FUNCTION ###

    def liffPermision(self):
        data = {
            'on': [
                'P',
                'CM'
                ],
            'off': []
            }
        headers = copy.deepcopy(self.headers)
        headers["Content-Type"] = "application/json"
        headers["X-Line-ChannelId"] = "1586794970"
        requests.post('https://access.line.me/dialog/api/permissions', json=data, headers=headers)
        return

    def postSticker(self, to, url):
        data = {
            "type": "template",
            "altText": "Boteater Team",
            "template": {
                "type": "image_carousel",
                "columns": [
                    {
                        "imageUrl": url,
                        "size": "full",
                        "action": {
                            "type": "uri",
                            "uri" : "https://boteater.us/"
                            }
                        }
                    ]
                }
            }
        liff_struct = LiffViewRequestStruct(
            liffId="1586794970-VKzbNLP7",
            context=LiffContextStruct(chat=ChatContextStruct(to)),
            lang="en_ID"
            )
        bearer = self.liff.issueLiffView(liff_struct).accessToken
        headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 4.4.2; SM-N950N Build/NMF26X) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/30.0.0.0 Mobile Safari/537.36 (Mobile; afma-sdk-a-v12529005.12451000.1)',
                   'Content-Type': 'application/json',
                   'Authorization': 'Bearer {}'.format(bearer)}
        result = requests.post(self.liffServer, json={"messages":[data]}, headers=headers)
        if result.status_code != 200:
            raise Exception("[ Error ] Fail post sticker")
        return


    def postVideo(self, to, url):
        data = {
            "type": "video",
            "originalContentUrl": url,
            "previewImageUrl": "https://boteater.us/logo.jpg"
            }
        liff_struct = LiffViewRequestStruct(
            liffId="1586794970-VKzbNLP7",
            context=LiffContextStruct(chat=ChatContextStruct(to)),
            lang="en_ID"
            )
        bearer = self.liff.issueLiffView(liff_struct).accessToken
        headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 4.4.2; SM-N950N Build/NMF26X) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/30.0.0.0 Mobile Safari/537.36 (Mobile; afma-sdk-a-v12529005.12451000.1)',
                   'Content-Type': 'application/json',
                   'Authorization': 'Bearer {}'.format(bearer)}
        result = requests.post(self.liffServer, json={"messages":[data]}, headers=headers)
        if result.status_code != 200:
            raise Exception("[ Error ] Fail post video")
        return


    def postImage(self, to, url):
        data = {
            "type": "image",
            "originalContentUrl": url,
            "previewImageUrl": url
            }
        liff_struct = LiffViewRequestStruct(
            liffId="1586794970-VKzbNLP7",
            context=LiffContextStruct(chat=ChatContextStruct(to)),
            lang="en_ID"
            )
        bearer = self.liff.issueLiffView(liff_struct).accessToken
        headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 4.4.2; SM-N950N Build/NMF26X) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/30.0.0.0 Mobile Safari/537.36 (Mobile; afma-sdk-a-v12529005.12451000.1)',
                   'Content-Type': 'application/json',
                   'Authorization': 'Bearer {}'.format(bearer)}
        result = requests.post(self.liffServer, json={"messages":[data]}, headers=headers)
        if result.status_code != 200:
            raise Exception("[ Error ] Fail post image")
        return

    def postAudio(self, to, url):
        data = {
            "type": "audio",
            "originalContentUrl": url,
            "duration": 1000
            }
        liff_struct = LiffViewRequestStruct(
            liffId="1586794970-VKzbNLP7",
            context=LiffContextStruct(chat=ChatContextStruct(to)),
            lang="en_ID"
            )
        bearer = self.liff.issueLiffView(liff_struct).accessToken
        headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 4.4.2; SM-N950N Build/NMF26X) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/30.0.0.0 Mobile Safari/537.36 (Mobile; afma-sdk-a-v12529005.12451000.1)',
                   'Content-Type': 'application/json',
                   'Authorization': 'Bearer {}'.format(bearer)}
        result = requests.post(self.liffServer, json={"messages":[data]}, headers=headers)
        if result.status_code != 200:
            raise Exception("[ Error ] Fail post audio")
        return

    def postFlex(self, to, data):
        liff_struct = LiffViewRequestStruct(
            liffId="1586794970-VKzbNLP7",
            context=LiffContextStruct(chat=ChatContextStruct(to)),
            lang="en_ID"
            )
        bearer = self.liff.issueLiffView(liff_struct).accessToken
        headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 4.4.2; SM-N950N Build/NMF26X) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/30.0.0.0 Mobile Safari/537.36 (Mobile; afma-sdk-a-v12529005.12451000.1)',
                   'Content-Type': 'application/json',
                   'Authorization': 'Bearer {}'.format(bearer)}
        result = requests.post(self.liffServer, json={"messages":[data]}, headers=headers)
        if result.status_code != 200:
            raise Exception("[ Error ] Fail post flex")
        return

    def linkSendMessage(self, msg):
        return "line://app/1586794970-VKzbNLP7?act=msg&text="+msg

    def linkSendVideo(self, url):
        return "line://app/1586794970-VKzbNLP7?act=video&url="+url

    def linkSendAudio(self, url):
        return "line://app/1586794970-VKzbNLP7?act=audio&url="+url

    def linkSendImage(self, url):
        return "line://app/1586794970-VKzbNLP7?act=pict&url="+url


    ### TIMELINE FUNCTION ###

    def getProfileDetail(self, mid):
        return json.loads(requests.get(self.lineServer+"/mh/api/v1/userpopup/getDetail.json?userMid="+mid, headers=self.tl_headers).text)

    def getProfileCoverURL(self, mid):
        home = self.get_timeline_user(mid)
        return self.lineOBS+'/myhome/c/download.nhn?userid='+mid+'&oid='+home['result']['objectId']

    def getTimelineURL(self, mid):
        link = self.lineServer+"/mh/api/v51/web/getUrl.json?homeId="+mid
        return json.loads(requests.get(link, headers=self.tl_headers).text)["result"]["homeWebUrl"]

    def getGroupPost(self, mid):
        link = self.lineServer+"/mh/api/v51/post/list.json?postLimit=999&commentLimit=999&likeLimit=999&homeId="+mid
        return json.loads(requests.get(link, headers=self.tl_headers).text)

    def likePost(self, mid, postId):
        data = {'contentId': postId,
                'actorId': mid,
                'likeType': random.choice([1001,1002,1003,1004,1005,1006])
                }
        link = self.lineServer+'/mh/api/v51/like/create.json?homeId='+mid
        return json.loads(requests.post(link, headers=self.tl_headers, data=json.dumps(data)).text)

    def createComment(self, mid, postId, text):
        data = {'contentId': postId,
                'actorId': mid,
                'commentText': text,
                'contentsList': [],
                'recallInfos': []
                }
        link = self.lineServer+'/mh/api/v51/comment/create.json?homeId='+mid
        return json.loads(requests.post(link, headers=self.tl_headers, data=json.dumps(data)).text)

    def updateProfilePciture(self, picture):
        headers = copy.deepcopy(self.headers)
        headers["X-Line-Access"] = self.tokenOBS
        headers["content-type"] = "image/png"
        obs= self.genOBSParams({"name":"profile.jpg", "type":"image", "ver":"2.0"})
        headers["x-obs-params"] = obs
        result = requests.post(self.lineOBS + "/r/talk/p/" + self.profile.mid, headers=headers, data=open(picture, 'rb'))
        if result.status_code != 201:
            raise Exception("[ Error ] Fail change profile picture")
        return

    def updateProfileVideo(self, picture, video):
        headers = copy.deepcopy(self.headers)
        headers["X-Line-Access"] = self.tokenOBS
        headers["content-type"] = "video/mp4"
        obs= self.genOBSParams({"name": video, "type":"video", "ver":"2.0", "cat":"vp.mp4"})
        headers["x-obs-params"] = obs
        result = requests.post(self.lineOBS + "/r/talk/vp/" + self.profile.mid, headers=headers, data=open(video, 'rb'))
        if result.status_code != 201:
            raise Exception("Fail change vp")
        headers = copy.deepcopy(self.headers)
        headers["X-Line-Access"] = self.tokenOBS
        headers["content-type"] = "image/png"
        obs= self.genOBSParams({"name":"profile.jpg", "type":"image", "ver":"2.0", "cat":"vp.mp4"})
        headers["x-obs-params"] = obs
        result = requests.post(self.lineOBS + "/r/talk/p/" + self.profile.mid, headers=headers, data=open(picture, 'rb'))
        if result.status_code != 201:
            raise Exception("[ Error ] Fail change video profile")
        return

    def updateCover(self, picture):
        oid = self.genObjectId()
        headers = copy.deepcopy(self.tl_headers)
        headers["X-Line-PostShare"] = "false"
        headers["X-Line-StoryShare"] = "false"
        headers["x-line-signup-region"] = "ID"
        headers["content-type"] = "image/png"
        obs= self.genOBSParams({"name": picture, "oid": oid, "type": "image", "userid": self.profile.mid, "ver":"2.0"})
        headers["x-obs-params"] = obs
        result = requests.post(self.lineOBS + "/r/myhome/c/" + oid, headers=headers, data=open(picture, 'rb'))
        if result.status_code != 201:
            raise Exception("[ Error ] Fail change cover")
        return

    

    ### USER FUNCTION ###

    def acquireEncryptedAccessToken(self, featureType=1):
        return self.talk.acquireEncryptedAccessToken(featureType)

    def issueChannelToken(self, channelId):
        return self.channel.issueChannelToken(channelId)

    def getChannelInfo(self, channelId):
        return self.channel.getChannelInfo(channelId, "ID")

    def getSettings(self):
        return self.talk.getSettings()

    def getSettingsAttributes(self, attrBitset):
        return self.talk.getSettingsAttributes(attrBitset)

    def getSettingsAttributes2(self, attributesToRetrieve):
        return self.talk.getSettingsAttributes2(attributesToRetrieve)

    def getProfile(self):
        return self.talk.getProfile()

    def getFriendRequests(self, direction, lastSeenSeqId):
        return self.talk.getFriendRequests(direction, lastSeenSeqId)

    def removeFriendRequest(self, direction, midOrEMid):
        return self.talk.removeFriendRequest(direction, midOrEMid)

    def generateUserTicket(self, expirationTime=100, maxUseCount=100):
        return self.talk.generateUserTicket(expirationTime, maxUseCount)

    def updateProfile(self, profileObject):
        return self.talk.updateProfile(0, profileObject)

    def updateSettingsAttribute(self, attr, value):
        return self.talk.updateSettingsAttribute(0, attr, value)
    
    def updateSettingsAttributes2(self, attributesToUpdate, settings):
        return self.talk.updateSettingsAttributes2(0, attributesToUpdate, settings)

    def updateProfileAttribute(self, attrId, value):
        return self.talk.updateProfileAttribute(0, attrId, value)
    

    
    ### OPERATION FUNCTION ###

    def fetchOperation(self, count=20):
        return self.pool.fetchOps(self.lastOP, count, self.lastOP, self.lastOP)

    def getLastOpRevision(self):
        return self.talk.getLastOpRevision()



    ### MESSAGE FUNCTION ###
    
    def sendMessage(self, to, text, contentMetadata={}, contentType=0):
        msg = MessageStruct()
        msg.to, msg._from = to, self.profile.mid
        msg.text = text
        msg.contentType, msg.contentMetadata = contentType, contentMetadata
        return self.talk.sendMessage(0, msg)

    def sendMessageReply(self, to, text, msgId):
        msg = MessageStruct()
        msg.to, msg._from = to, self.profile.mid
        msg.text = text
        msg.contentType, msg.contentMetadata = 0, {}
        msg.relatedMessageId = msgId
        msg.messageRelationType = 3
        msg.relatedMessageServiceCode = 1
        return self.talk.sendMessage(0, msg)

    def sendMessageWithMention(self, to, text='', dataMid=[]):
        arr = []
        list_text=''
        if '[list]' in text.lower():
            i=0
            for l in dataMid:
                list_text+='\n@[list-'+str(i)+']'
                i=i+1
            text=text.replace('[list]', list_text)
        elif '[list-' in text.lower():
            text=text
        else:
            i=0
            for l in dataMid:
                list_text+=' @[list-'+str(i)+']'
                i=i+1
            text=text+list_text
        i=0
        for l in dataMid:
            mid=l
            name='@[list-'+str(i)+']'
            ln_text=text.replace('\n',' ')
            if ln_text.find(name):
                line_s=int(ln_text.index(name))
                line_e=(int(line_s)+int(len(name)))
            arrData={'S': str(line_s), 'E': str(line_e), 'M': mid}
            arr.append(arrData)
            i=i+1
        contentMetadata={'MENTION':str('{"MENTIONEES":' + json.dumps(arr).replace(' ','') + '}')}
        return self.sendMessage(to, text, contentMetadata)

    def sendContact(self, to, mid):
        return self.sendMessage(to, '', {'mid': mid}, 13)

    def sendImage(self, to, path):
        objectId = self.sendMessage(to=to, text=None, contentType = 1).id
        return self.uploadObjTalk(path=path, type='image', objId=objectId)

    def sendGIF(self, to, path):
        return self.uploadObjTalk(path=path, type='gif', to=to)

    def sendVideo(self, to, path):
        objectId = self.sendMessage(to=to, text=None, contentMetadata={'VIDLEN': '1000','DURATION': '1000'}, contentType = 2).id
        return self.uploadObjTalk(path=path, type='video', objId=objectId)

    def sendAudio(self, to, path):
        objectId = self.sendMessage(to=to, text=None, contentType = 3).id
        return self.uploadObjTalk(path=path, type='audio', objId=objectId)

    def sendFile(self, to, path, file_name=None):
        if file_name == None:
            file_name = ntpath.basename(path)
        file_size = len(open(path, 'rb').read())
        objectId = self.sendMessage(to=to, text=None, contentMetadata={'FILE_NAME': str(file_name),'FILE_SIZE': str(file_size)}, contentType = 14).id
        return self.uploadObjTalk(path=path, type='file', objId=objectId)

    def sendChatChecked(self, chatMid, lastMessageId):
        return self.talk.sendChatChecked(0, chatMid, lastMessageId)
    
    def unsendMessage(self, messageId):
        return self.talk.unsendMessage(0, messageId)

    def removeAllMessages(self, lastMessageId):
        return self.talk.removeAllMessages(0, lastMessageId)

    def sendChatRemoved(self, chatMid, lastMessageId, sessionId):
        return self.talk.sendChatRemoved(0, chatMid, lastMessageId, sessionId)

    

    ### CONTACT FUNCTION ###

    def blockContact(self, mid):
        return self.talk.blockContact(0, mid)

    def unblockContact(self, mid):
        return self.talk.unblockContact(0, mid, "")

    def findAndAddContactsByMid(self, mid):
        return self.talk.findAndAddContactsByMid(0, mid, 0, '')

    def findAndAddContactsByUserid(self, searchId):
        return self.talk.findAndAddContactsByUserid(0, searchId)

    def findAndAddContactsByPhones(self, phones=[]):
        return self.talk.findAndAddContactsByPhone(0, phones)

    def getAllContactIds(self):
        return self.talk.getAllContactIds()

    def getBlockedContactIds(self):
        return self.talk.getBlockedContactIds()

    def getContact(self, mid):
        return self.talk.getContact(mid)

    def updateContactSetting(self, mid, flag, value):
        return self.talk.updateContactSetting(mid)



    ### GROUP FUNCTION ###

    def getGroupWithoutMembers(self, groupId):
        return self.talk.getGroupWithoutMembers(groupId)

    def findGroupByTicket(self, ticketId):
        return self.talk.findGroupByTicket(ticketId)

    def acceptGroupInvitation(self, groupId):
        return self.talk.acceptGroupInvitation(0, groupId)

    def acceptGroupInvitationByTicket(self, groupMid, ticketId):
        return self.talk.acceptGroupInvitationByTicket(0, groupMid, ticketId)

    def cancelGroupInvitation(self, groupId, contactIds=[]):
        return self.talk.cancelGroupInvitation(0, groupId, contactIds)

    def createGroupV2(self, name, contactIds=[]):
        return self.talk.createGroupV2(0, name, midlist)

    def getGroup(self, groupId):
        return self.talk.getGroup(groupId)

    def getCompactGroup(self, groupId):
        return self.talk.getCompactGroup(groupId)

    def getGroupIdsInvited(self):
        return self.talk.getGroupIdsInvited()

    def getGroupIdsJoined(self):
        return self.talk.getGroupIdsJoined()

    def getGroup(self, groupId):
        return self.talk.getGroup(groupId)

    def getGroupsV2(self, groupIds):
        return self.talk.getGroupsV2(groupIds)

    def updateGroupPreferenceAttribute(self, groupMid, updatedAttrs):
        return self.talk.updateGroupPreferenceAttribute(0, groupMid, updatedAttrs)

    def inviteIntoGroup(self, groupId, contactIds=[]):
        return self.talk.inviteIntoGroup(0, groupId, contactIds)

    def kickoutFromGroup(self, groupId, contactIds=[]):
        return self.talk.kickoutFromGroup(0, groupId, contactIds)

    def leaveGroup(self, groupId):
        return self.talk.leaveGroup(0, groupId)

    def rejectGroupInvitation(self, groupId):
        return self.talk.rejectGroupInvitation(0, groupId)

    def reissueGroupTicket(self, groupMid):
        return self.talk.reissueGroupTicket(groupMid)

    def updateGroup(self, group):
        return self.talk.updateGroup(0, group)

    

    ### CALL FUNCTION ###
    
    def acquireGroupCallRoute(self, chatMid, isInitialHost=True, capabilities=[]):
        return self.call.acquireGroupCallRoute(chatMid, 1, isInitialHost, capabilities)

    def getGroupCall(self, chatMid):
        return self.call.getGroupCall(chatMid)

    def inviteIntoGroupCall(chatMid, memberMids=[]):
        return self.call.inviteIntoGroupCall(chatMid, memberMids, 1)


    ### ROOM FUNCTION ###
    
    def createRoomV2(self, contactIds=[]):
        return self.talk.createRoomV2(0, contactIds)

    def getRoomsV2(self, roomIds=[]):
        return self.talk.getRoomsV2(roomIds)

    def inviteIntoRoom(self, roomId, contactIds=[]):
        return self.talk.inviteIntoRoom(0, roomId, contactIds)

    def leaveRoom(self, roomId):
        return self.talk.leaveRoom(0, roomId)



    ### SHOP FUNCTION ###

    def getProductSticker(self, productId):
        return self.shop.getProduct("stickershop", productId, "ID")

    def getProductTheme(self, productId):
        return self.shop.getProduct("themshop", productId, "ID")

    def getProductV2Sticker(self, productId):
        data = GetProductRequestStruct()
        data.productType = 1
        data.productId = productId
        data.carrierCode = "510012"
        data.saveBrowsingHistory = False
        return self.shop.getProductV2(data)

    def getProductV2Theme(self, productId):
        data = GetProductRequestStruct()
        data.productType = 2
        data.productId = productId
        data.carrierCode = "510012"
        data.saveBrowsingHistory = False
        return self.shop.getProductV2(data)

    def placePurchaseOrderForFreeProduct(self, to, productId):
        info = self.getProductV2Sticker(productId)
        locale = LocaleStruct()
        locale.language = "EN"
        locale.country = "ID"
        data = PurchaseOrderStruct()
        data.shopId = "stickershop"
        data.productId = productId
        data.recipientMid = to
        data.price = info.productDetail.price
        data.enableLinePointAutoExchange= True
        data.locale = locale
        data.presentAttributes = {}
        return self.shop.placePurchaseOrderForFreeProduct(data)

    def placePurchaseOrderWithLineCoin(self, to, productId):
        info = self.getProductV2Sticker(productId)
        locale = LocaleStruct()
        locale.language = "EN"
        locale.country = "ID"
        data = PurchaseOrderStruct()
        data.shopId = "stickershop"
        data.productId = productId
        data.recipientMid = to
        data.price = info.productDetail.price
        data.enableLinePointAutoExchange= True
        data.locale = locale
        data.presentAttributes = {}
        return self.shop.placePurchaseOrderWithLineCoin(data)

    def genStickerLink(self, productId):
        patern = copy.deepcopy(self.stickerLinkAnimation)
        link = patern.format(productId)
        r = requests.get(link)
        if r.status_code == 200:
            return link
        patern = copy.deepcopy(self.stickerLink)
        link = patern.format(productId)
        r = requests.get(link)
        if r.status_code == 200:
            return link
        return None
    
    ### REPORT FUNCTION ###

    def report(self, syncOpRevision, category, reason):
        return self.talk.report(syncOpRevision, category, reason)



    ### LOGIN FUNCTION ###
    def qrLogin(self, headers):
        sys_name = "BE-Team"
        transport = THttpClient(self.lineServer + '/api/v4/TalkService.do')
        transport.setCustomHeaders(headers)
        protocol = TCompactProtocol(transport)
        talk = BoteaterService.Client(protocol)
        qr_code = talk.getAuthQrcode(keepLoggedIn=True, systemName=sys_name, returnCallbackUrl=True)
        transport.close()
        print(qr_code.callbackUrl)
        headers["X-Line-Access"] = qr_code.verifier
        transport = THttpClient(self.lineServer + '/api/v4p/rs')
        transport.setCustomHeaders(headers)
        protocol = TCompactProtocol(transport)
        auth = BoteaterService.Client(protocol)
        get_access = json.loads(requests.get(self.lineServer + '/Q', headers=headers).text)
        login_request = LoginRequestStruct()
        login_request.type = 1
        login_request.identityProvider = 1
        login_request.keepLoggedIn = True
        login_request.systemName = sys_name
        login_request.verifier = get_access['result']['verifier']
        result = auth.loginZ(login_request)
        transport.close()
        return result.authToken

    def qrLoginRotate(self, header):
        if header in ["ios_ipad", "chrome"]:
            result = json.loads(requests.get(self.boteaterApi + "/qr?header=" + header).text)
            if result["status"] == 200:
                print(result["result"]["qr_link"])
                print("Login Target: " + result["result"]["login_ip"])
                result = json.loads(requests.get(result["result"]["callback"]).text)
                if result["status"] == 200:
                    return result["result"]
                else:
                    raise Exception("[ Error ] Rotate QR Login")
            else:
                raise Exception("[ Error ] Rotate QR Login")
