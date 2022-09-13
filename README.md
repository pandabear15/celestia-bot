# Celestia-Bot
UW Genshin Discord's custom moderation bot.

Celestia monitors and logs edit and delete actions on the server for the purposes of accountability and safety.
For questions about the bot, please contact RicePulp#0077 and/or Purost#1025.

## Version 1.0.2
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
- Delete logs do not display attachments for context messages.

## Version 1.0.1
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
- Celestia's error logs are suboptimal and could provide more information or context about errors.
- The edit embed displays attachments illogically and should display "Attachments before edit" directly after the "Before"
section. It should also display the attachments remaining after the edit. **Addressed in Version 1.0.2.**
- Currently, after a message is deleted, the message cache still lives in the internal cache, which is an unnecessary
use of resources. **Addressed in Version 1.0.2.**
- The bot is currently hosted locally, and is planned to be migrated to a hosting service. This change will occur with 
Version 1.1.0.

## Version 1.0.0
Initial release.