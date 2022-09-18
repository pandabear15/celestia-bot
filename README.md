# Celestia-Bot
UW Genshin Discord's custom moderation bot.

Celestia monitors and logs edit and delete actions on the server for the purposes of accountability and safety.
For questions about the bot, please contact RicePulp#0077 and/or Purost#1025.

## Version 1.1.0
Released on XXXX
### Features
- Celestia is now hosted on Amazon Web Service (AWS) EC2. This change ensures that uptime on the bot is not reliant on 
uptime of a personal computer, especially one that needs to be turned off for an extended period of time in the near 
future. This also prevents the devs from accidentally stopping the process running the bot.
  - EC2 is free for an entire year, after which cost is around $5/month.
- Celestia's "+info" command now displays more information about Celestia's internal state, such as memory consumption
and cache writing execution times.
  - This is especially important as after hosting, the console and console logs will be much harder to access, so being
able to query Celestia directly for this information will make monitoring the bot much simpler.
- The command "+error" now causes Celestia to throw an error. This, along with "+info", can only be called by admins in
the logs channel.
  - The purpose of this command is to be able to access and test an error message without an error actually occurring.
### Bug Fixes
- Fixed a bug that caused Celestia to read content strings in the cache file to be interpreted in the wrong encoding
scheme.
  - Technically, nothing had to be done to fix this bug as it was never a bug in the first place. The dev team only
    logged this bug because the log structure looked wrong, but it turns out that everything was actually working as
    intended.
- Fixed a bug that prevented Celestia from providing extra context on error messages.
### Other changes
- Small consistency/wording changes to previous version logs.
### Known issues
- None so far, but the dev team will be monitoring the bot closely over the next few days to ensure everything is going
smoothly with the transfer to AWS EC2.
- The dev team would also like to note that the updated sticker handling is still on the to-do list; it has not been
forgotten.

## Version 1.0.3
Released on 2022-09-15 13:23-07:00.
### Features
- The 'Welcome' and 'Important' categories in the server are no longer monitored by Celestia.
- Delete logs now also include attachment information for context messages.
- The command "+info" now displays basic information about Celestia and its current status.
### Bug fixes
- Fixed an issue that caused context messages with textual content to appear as if they had no textual content.
  - This issue also could sometimes cause Celestia to error out.
### Other changes
- Celestia's error logs now print more context on the immediate cause of the error.
- README.md now includes the time that each version was pushed.
### Known issues
- ~~Messages that were cached in the cache file render as raw strings instead of in the proper encoding scheme (UTF-16).~~
**Addressed in Version 1.1.0.**
  - ~~Until this issue is fixed, fast booting may cause unexpected rendering errors, so unfortunately we must still use 
    slow-booting.~~

## Version 1.0.2
Released on 2022-09-13 00:08-07:00.
### Features
- Reworked the edit and delete logs to display attachments directly after the message that contained them.
### Bug fixes
- Fixed an issue that caused messages posted during Celestia's booting up period to appear in the cache twice.
- Fixed an issue that caused edit messages to display a coroutine object instead of the proper Discord message in the
'After' field.
### Other changes
- Deleted message, after logging, are now also deleted from the internal cache, optimizing memory usage.
- Metrics on reading and writing to the cache file are now recorded to the console.
- Reversed the versioning order in README.md.
  - This change aligns with typical versioning logs, beginning with the most recent version.
- Minor QOL fixes.
### Known issues
- ~~Delete logs do not display attachments for context messages.~~ **Addressed in Version 1.0.3.**

## Version 1.0.1
Released on 2022-09-12 21:31-07:00.
### Features
- Added the ability for Celestia to write the current cache to a .txt file. This is expected to improve back-logging 
performance for future boot performance.
- Added the ability for Celestia to ignore certain categories as defined in the .conf/config file. This is expected to 
improve boot performance for back-logging by ignoring channels that do not require monitoring.
### Bug fixes
- Fixed an issue that caused Discord-triggered embed edits to appear as edits triggered by the poster.
- Fixed an issue that caused Celestia to error out on post deletion if previous messages had empty bodies 
(e.g. a sticker-only message).
### Other changes
- Temporarily reverted the ability for Celestia to post a sticker image in a delete log, instead posting the sticker 
name surrounded by colons as if it were an emote.
  - The motivation for this change is that embeds do not support forcing image dimensions, which could result in visually
  very large images being included in logs. A better solution for stickers is being worked on.
- Changed the indication of a message with empty body from "_\[Empty message\]_" to "_\[Empty message body\]_" for clarity.
  - "Empty message body" clarifies that the message has no text, but could have, for example, attachments or stickers.
- Various consistency and quality of life changes.
### Known issues
- ~~Celestia's error logs are suboptimal and could provide more information or context about errors.~~ **Addressed in Version
1.0.3.**
- ~~The edit embed displays attachments illogically and should display "Attachments before edit" directly after the "Before"
section. It should also display the attachments remaining after the edit.~~ **Addressed in Version 1.0.2.**
- ~~Currently, after a message is deleted, the message cache still lives in the internal cache, which is an unnecessary
use of resources.~~ **Addressed in Version 1.0.2.**
- ~~The bot is currently hosted locally, and is planned to be migrated to a hosting service. This change will occur with 
Version 1.1.0.~~ **Addressed in Version 1.1.0.**

## Version 1.0.0
Released on 2022-09-10 22:32-07:00.