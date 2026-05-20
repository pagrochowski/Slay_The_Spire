The task is to refactor and redo this project cleanly. It is quite a mess, so we need to make a good plan to redo this. 

data folder contains knowledge base for characters, cards, relics, potions, bosses, etc. 

logs folder should contain logs about every activity that the script is taking, every step should be documented, so it can be retracted and checked for debugging. it must be very comprehensive with timestamps and every step of the process needs to make a mark there. 

scripts_old and src_old folders contain scripts, most of them are now redundant, please check the folder and remove everything that is not needed anymore. The remaining ones will be used as references when we rebuild each functionality one by one. 

How the voice recorder should work from now on:

1. Make a copy of the save file of the game. We never want to work on the live save file to avoid corruption. Backups are to be deleted once daily, so any backup older than 24 hours can be deleted.
2. Parse the copied save file into json file and store its contents for processing. 
3. Parsed JSON file is used to extract current run summary and to create a Run_Summary.md document. Make sure the sections are populated correctly. Deck cards - each card should be in one line. Duplicated cards need to contain the multiplier instead of listing them multiple times. Cards need to contain descriptions and energy cost, relics with descriptions and potions with descriptions. 
4. When user presses F1, the voice recorder is activated. The user then speaks names of cards or relics and recorder adds them to the current choice section in summary md file. 
5. Currently Groq API is handling the understanding of the voice. Sometimes, the voice is not recorded clearly, so certain names can be misspelled. This is where we need the power of LLM to infer what the user intended to say, what names they wanted to add. 
6. In order to help LLM make the right choice, we need to add all card and relic names that are possible for the class currently being played. For example, if user is playing Ironclad, the LLM prompt will contain all cards used by all classes, but also Ironclad specific, but not Silent specific cards.
7. The current choice section always contains "- SKIP?" at the end
8. regenerate AI_GUID.md file for an AI assistant to use as technical knowledgebase

Please make a plan to implement this and ask me follow up questions. 


1. saves are located here, you will find references to it in the _old folders
c:\Games\Slay.the.Spire.v2.3.4\Slay.the.Spire.v2.3.4\saves\

2. yes, this was already implemente this way

3. Yes, replace it each time with new current choice

4. yes, continue using groq, check _old folders to see which 4 models have been used. we need to implement similar fallback strategy as before as well to avoid long waiting times and jump between models as they may hit errors or quota issues.

5. Everything you would include in a technical handover document to another AI developer agent for project context. 

6. yes run automatically on startup. 

7. remove the choice mode flag, it was used before, but not necessary anymore. 

8. exclude other class cards to reduce noise, we only want to give a pool of possible cards to LLM to decide which are the best match for what the user said. 

9. Actually, keep all of them for reference and check each one when creating new functionality, as there may be hints on technical solutions, but we want to recreate the scripts and src files, since previous ones are too messy. we need a clean, fresh start now. 

10. please put test units into tests folder, I would like to go step by step with functionality and make sure everything works before we move to the next piece. let's do it professionally. 