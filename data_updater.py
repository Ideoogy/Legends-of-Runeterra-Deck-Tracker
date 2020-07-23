
import requests
import json
import tkinter as tk
import psutil
import time
import os.path
import urllib.request
import shutil
from zipfile import ZipFile
from fast_autocomplete import AutoComplete

curDeckURL = "http://localhost:21337/static-decklist"
lastGameURL = "http://localhost:21337/game-result"
cardPosURL = "http://localhost:21337/positional-rectangles"
dd_url = "https://dd.b.pvp.net/datadragon-set1-en_us.zip"
menu_img = "http://runetracker.gg/wp-content/uploads/2019/11/menu_img.zip"


decklist = {}
cardsDrawn = {}
unitsPlayed = {}
unitsDied = {}
spellsCasted = {}

def first_run():
    if (os.path.exists(os.getcwd() + "/img")):
        return
    print("Doing First Time Work!")
    urllib.request.urlretrieve(dd_url, os.getcwd() + '/ddragon.zip')
    print("Download Completed. Beginning Unzip")
    with ZipFile(os.getcwd() + '/ddragon.zip', 'r') as zipObj:
        for fileName in zipObj.namelist():
            if fileName.endswith('.png'):
                zipObj.extract(fileName, os.getcwd() + '/unzip/')
            if fileName.endswith('en_us.json'):
                zipObj.extract(fileName, os.getcwd())
    source = os.getcwd() + '/unzip/en_us/img/cards/'
    urllib.request.urlretrieve(menu_img, os.getcwd() + '/menu_img.zip')
    with ZipFile(os.getcwd() + '/menu_img.zip', 'r') as zipObj:
        zipObj.extractall()
    try:
        os.makedirs(os.getcwd() + '/img') ## it creates the destination folder
    except:
        print("Folder already exists")
    for f in os.listdir(source):
        shutil.move(source + f, os.getcwd() + '/img/')
    for f in os.listdir(os.getcwd() + '/en_us/data/'):
        shutil.move(os.getcwd() + '/en_us/data/' + f, os.getcwd())
    shutil.rmtree(os.getcwd() + '/en_us')
    shutil.rmtree(os.getcwd() + '/unzip')    
    os.remove(os.getcwd() + '/ddragon.zip')
    return

def getDecklist():
    global decklist
    parsedData = parseRiot()
    try:
        print("Grabbing decklist")
        r = requests.post(url = curDeckURL)
        decklist = r.json()
    except requests.exceptions.RequestException:
        print("Connection failed")
        return(None)


    #TEMPORARY CODE
    #active_deck = open("active_deck.json", 'r', encoding="utf8")
    #decklist = json.load(active_deck)
    
    if(decklist['CardsInDeck'] == None):
        print("No cards in deck found")
        return(None)
    decklist['DeckCode'] = decklist['DeckCode']
    print("Iterating through decklist")
    for key in decklist['CardsInDeck'].keys():
        newKey = {'Count': decklist['CardsInDeck'][key]}
        newKey['Name'] = parsedData[key]['name']
        newKey['Type'] = parsedData[key]['type']
        newKey['SpellSpeed'] = parsedData[key]['spellSpeed']
        decklist['CardsInDeck'][key] = newKey

    return(decklist)
    
def parseRiot():
    parsedData = {}
    if(os.path.exists("parsedRiot.json")):
        return(json.load(open("parsedRiot.json", 'r', encoding="utf8")))
    else:
        with open('set1-en_us.json', 'r', encoding="utf8") as riotDataFile:
            riotData = json.load(riotDataFile)
            #Reformat the riot data file for easier use.
            for card in riotData:
                cardCode= card['cardCode']
                parsedData[cardCode] = card
            riotDataFile.close()
        parsedRiot = open("parsedRiot.json", 'w', encoding="utf8")
        parsedRiot.write(json.dumps(parsedData, sort_keys=True, indent=4, separators=(',', ': ')))
        parsedRiot.close()
    return(parsedData)

def writeRecordsFile(gameInfo, lastGame):
    global parsedRecords, decklist
    try:
        recordFile = open("records.json", 'r', encoding="utf8")
        parsedRecords = json.load(recordFile)
        recordFile.close()
    except IOError:
        parsedRecords = {}
    except json.decoder.JSONDecodeError:
        parsedRecords={}

    with open("records.json", 'w+', encoding="utf8") as recordFile:
        dc = decklist['DeckCode']
        parsedRecords.setdefault(dc, {})
        parsedRecords[dc]['CardsInDeck'] = decklist["CardsInDeck"]
        parsedRecords[dc].setdefault("PlayerWins", {})
        parsedRecords[dc].setdefault("PlayerLosses", {})
        parsedRecords[dc].setdefault("TotalLosses", 0)
        parsedRecords[dc].setdefault("TotalWins", 0)
        parsedRecords[dc]["CardsInDeck"] = decklist['CardsInDeck']
        if (lastGame["LocalPlayerWon"]):
            oldPWins = parsedRecords[dc]["PlayerWins"].setdefault(gameInfo["OpponentName"], 0)
            parsedRecords[dc]["PlayerWins"][gameInfo["OpponentName"]] = oldPWins + 1
            parsedRecords[dc]["TotalWins"]+=1
        else:
            print(parsedRecords[dc])
            oldPLosses = parsedRecords[dc]["PlayerLosses"].setdefault(gameInfo["OpponentName"], 0)
            parsedRecords[dc]["PlayerLosses"][gameInfo["OpponentName"]] = oldPLosses + 1
            oldLosses = parsedRecords[dc].setdefault("TotalLosses", 0)
            print(oldLosses)
            parsedRecords[dc]["TotalLosses"]+=1
        recordFile.write(json.dumps(parsedRecords, sort_keys=True, indent=4, separators=(',', ': ')))
        recordFile.close()

def checkGameStat(lastGameID, gameInfo, ready):
    if ("LoR.exe" not in (p.name() for p in psutil.process_iter())):
        print("Couldn't find program")
        print("Return values")
        print({'lastGameID': -1, 'gameInfo': None, 'ready': False})
        return({'lastGameID': -1, 'gameInfo': None, 'ready': False})
    print("Checking")
    try:
        r = requests.post(url = cardPosURL)
        gameInfo = r.json()
    except requests.exceptions.RequestException:
        print("Race condition in cardPos")
        return({'lastGameID': -1, 'gameInfo': None, 'ready': False})
    if(gameInfo["GameState"] == "In Progress"):
        print("In Progress")
    else:
        print("Not In Progress")
        ready = True
    r = requests.post(url = lastGameURL)
    lastGame = r.json()
    if(lastGame['GameID'] != lastGameID and ready):
        print("Game Finished")
        writeRecordsFile(gameInfo, lastGame)
        lastGameID = lastGame['GameID']
        ready = False
    print("Return Values")
    return({'lastGameID': lastGameID, 'gameInfo': gameInfo, 'ready': ready})

def checkForShuffleOnPlay(parsedData, card):
    print("CHECKING FOR SHUFFLE")
    if card == '01FR048':
        return (1,'01FR028')
    cardDescription = parsedData[card]['descriptionRaw'].lower()
    shuffleIndex = cardDescription.find('shuffle')
    lastBreathIndex = cardDescription.find('last breath:')
    if shuffleIndex != -1 and (lastBreathIndex == -1 or lastBreathIndex>shuffleIndex):
        intoIndex = cardDescription.find('into')
        parseString = cardDescription[shuffleIndex+8:intoIndex]
        print(f'{parseString}')
        nextIndex = parseString.find(' ')
        countString = parseString[:nextIndex]
        print(f'{countString}')
        if countString != 'a' and countString != 'an':
            count = int(countString)
        else:
            count = 1
        cardString = parseString[nextIndex+1:]
        print(f'{cardString}')
        for card in parsedData:
            if(parsedData[card]['name'].lower() == card_name):
                return (count, card)
    return None

def checkForShuffleOnDeath(parsedData, card):
    print("CHECKING FOR LAST BREATH SHUFFLE")
    cardDescription = parsedData[card]['descriptionRaw'].lower()
    shuffleIndex = cardDescription.find('shuffle')
    lastBreathIndex = cardDescription.find('last breath:')
    if shuffleIndex != -1 and -1<lastBreathIndex<shuffleIndex:
        intoIndex = cardDescription.find('into')
        parseString = cardDescription[shuffleIndex+8:intoIndex-1]
        print(f'{parseString}')
        nextIndex = parseString.find(' ')
        countString = parseString[:nextIndex]
        print(f'{countString}')
        if countString != 'a' and countString != 'an':
            count = int(countString)
        else:
            count = 1
        cardString = parseString[nextIndex+1:]
        print(f'{cardString}')
        for card in parsedData:
            if(parsedData[card]['name'].lower() == cardString):
                return (count, card)
    return None

def checkBoardState():
    global cardsDrawn, unitsPlayed, unitsDied, spellsCasted
    parsedData = parseRiot()
    r = requests.post(url = cardPosURL)
    gameInfo = r.json()
    #Might be needed in future
    boardHeight = gameInfo["Screen"]["ScreenHeight"]
    boardCenter = boardHeight/2
    playerBattleTopY = boardCenter - 0.055*boardHeight
    playerHandTopY = 0.09*boardHeight
    playerStandbyTopY = playerHandTopY + .164*boardHeight
    board = gameInfo["Rectangles"]
    cardsToRemove = []
    cardsToAdd = []
    boardIds = set()
    for card in board:
        cardCode = card["CardCode"]
        cardId = card["CardID"]   
        if cardCode in parsedData and card["LocalPlayer"] == True:
            cardTopY = card["TopLeftY"]                                             #Cards being hovered
            if cardId not in cardsDrawn and (cardTopY<playerHandTopY or playerBattleTopY<cardTopY<boardCenter):
                cardsToRemove.append(cardCode)
                cardsDrawn[cardId] = card
            elif cardId not in unitsPlayed and playerHandTopY<cardTopY<playerStandbyTopY and cardId in cardsDrawn:
                unitsPlayed[cardId] = card
                result = checkForShuffleOnPlay(parsedData, cardCode)
                if result is not None:
                    for i in range(result[0]):
                        cardsToAdd.append(result[1])
            elif cardId not in spellsCasted and parsedData[cardCode]['type'] == "Spell":
                spellsCasted[cardId] = card
        boardIds.add(cardId)
    removeList = []
    for cardId in spellsCasted:
        if cardId not in boardIds:
            cardCode = spellsCasted[cardId]["CardCode"]
            #spell should have been resolved if it's not on the board anymore
            result = checkForShuffleOnPlay(parsedData, cardCode)
            if result is not None:
                for i in range(result[0]):
                    cardsToAdd.append(result[1])
            removeList.append(cardId)
    for removeCardID in removeList:
        del spellsCasted[cardId]
    for cardId in unitsPlayed:
        if cardId not in boardIds and cardId not in unitsDied:
            unitsDied[cardId] = unitsPlayed[cardId]
            cardCode = unitsPlayed[cardId]["CardCode"]
            result = checkForShuffleOnDeath(parsedData, cardCode)
            if result is not None:
                    for i in range(result[0]):
                        cardsToAdd.append(result[1])
    return cardsToRemove, cardsToAdd

def dawg_generator(parsedData):
    autoDict = dict()
    for card in parsedData:
        autoDict[parsedData[card]["name"]] = {}
    return(autoDict)

def get_last_game_id():
    try:
        r = requests.post(url = lastGameURL)
    except requests.exceptions.RequestException:
        return(-1)
    lastGame = r.json()
    return(lastGame['GameID'])
