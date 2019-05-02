#!/usr/bin/env python3
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import shutil
from lxml import etree
import html
import vkbeautify
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


SPREADSHEetree_ID = '1Qk9V33adnHjXs8HM8wIFL13UMKhKihYWTduIe7csays'

def main():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)

    #
    
    shutil.rmtree('vocab', ignore_errors=True)
    os.mkdir('vocab')

    
    sheet_metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEetree_ID).execute()
    sheets = sheet_metadata.get('sheets', '')
    for sheet in sheets:
        title = sheet.get('properties').get('title')
        filename = sheet.get('properties').get('title').lower().replace(' ', '_')
        print(title, filename)

        googlesheet = service.spreadsheets().values().get(spreadsheetId=SPREADSHEetree_ID, range="{}!A2:C".format(title)).execute()
        
        vocab = etree.Element("opts")
        parentelement = None
        parentelementvalue = None
        for value in googlesheet.get('values', []):
            if len(value) == 1:
                element = etree.SubElement(vocab, "opt")
                element.text=html.escape(value[0])
            elif len(value) == 2:    
                element = etree.SubElement(vocab, "opt")            
                element.text=html.escape(value[0])
                desc = etree.SubElement(element, 'desc')
                desc.text=html.escape(value[1])
            elif len(value) == 3:               
                if value[0] != parentelementvalue:                    
                    parentelement = etree.SubElement(vocab, "opt")            
                    parentelement.text=html.escape(value[0])
                    parentelementvalue = value[0]
                element = etree.SubElement(parentelement, "opt")            
                element.text=html.escape(value[1])
                desc = etree.SubElement(element, 'desc')
                desc.text=html.escape(value[2])
            else:
                ValueError("Too many levels! Go implement some more!")
        
        tree = etree.ElementTree(vocab)
        tree.write("vocab/temp.xml", encoding="utf-8", pretty_print=True)
        vkbeautify.xml("vocab/temp.xml", "vocab/{}.xml".format(filename))
        os.remove("vocab/temp.xml")
        

if __name__ == '__main__':
    main()        