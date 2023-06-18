# Celestia-Bot
UW Genshin Discord's custom moderation bot.

Celestia monitors and logs edit and delete actions on the server for the purposes of accountability and safety.
For questions about the bot, please contact pandabear2, ricepulp and/or purost.

## Version 1.3.0
Released on 2023-06-18 14:56-07:00.
### Features
- This is technically not a feature, but is significant enough to mention that Celestia now correctly handles the new
Discord username changes.
- Celestia is now a music bot. Use the following commands to interact with the bot:
  - +join: summons Celestia to the voice chat and grants the caller music control.
  - +leave: dismisses Celestia and revokes all users of music control.
  - +search [string]: search for a song. Celestia responds with a list of the top five results.
  - +play [url or string]: immediately add a song from YouTube, or the top search result on YouTube to the queue.
  - +playnow [int]: stops the current song (if a song is being played) and starts playing the song in this position
  in the queue. Requires control permission.
  - +pause: pauses the current song. Requires control permission.
  - +resume: resumes the current song if music was paused or stopped. Requires control permission.
  - +stop: stops playback of current song, but keeps the current queue. Requires control permission.
  - +skip: skips current song and starts playing the next song in queue. Requires control permission.
  - +repeat [on/off]: requeues completed songs if on, disables this behavior if off. Default is off. Requires control permission.
  - +shuffle: shuffles the remaining queue. Requires control permission.
  - +clear: removes all songs from the queue. Does not stop the current song. Requires control permission.
  - +dequeue [int]: removes a song from the queue. Requires control permission to dequeue a song a user did not 
  add themselves.
  - +control: requests control of the music functionality of Celestia. Is automatically granted if no controller is 
  present in the call.
  - +control [username]: grants control of the music bot to a user. Control cannot be revoked once given until Celestia
  leaves the voice chat. Requires control permission.
  - +controllers: lists all current controllers of Celestia's music functionalities. 
  - +public: grants all users in the voice channel control permission, including users that join after this command is
  given. Cannot be revoked once given until Celestia leaves.
  - +playlist: views the current queue.
  - +current: views the current song if a song is playing.
### Known Issues
- Celestia currently does not recognize Spotify or other music-type links. Future updates may add this functionality.

## Version 1.2.1
Released on 2022-12-28 12:42-08:00.
### Features
- Celestia now has a 10% chance of sending the message "ok tyler 🎫" if the most recent message in a channel receives a
'🎫' reaction. Cooldown of one hour globally.
- Celestia now indicates and links to the message that a message replied to, if any, on delete logs.
### Bug fixes
- Fixed a bug where Celestia would completely ignore messages that were written in a reply to another message.
- Fixed various bugs that could arise if the cache contains zero entries.
### Other changes
- The command "+giveaway" has been depreciated.
### Known issues
- It is possible for message logs dealing with extremely long messages (currently only possible for users with Nitro) to
cause Celestia's message log to fail to send due to embed size limits.

## Version 1.2.0
Released on 2022-11-20 20:36-08:00.
### Features
- Celestia now counts pings in the birthday event channel. Ping count can be retrieved via the "+giveaway" command after 
the giveaway ends.
- Celestia now spoilers images in logs if they were spoilered when they were originally posted.
- "+status" is now the default command that retrieves Celestia's current state. "+info" is aliased to the status
command.
- Celestia now indicates whether a log message has already been sent to the bot developers via removing the "✉" emoji
and replacing it with the "📮" emoji. This also ensures that a log message cannot be sent twice.
### Bug fixes
None.
### Other changes
None.
### Known issues
- Currently, images cannot be automatically shared to devs by reacting with the mail emoji.
- Due to some edge case behavior regarding replies, rollout of the reply indication in logs as mentioned in the
Known issues section of 1.1.1 is delayed, and will hopefully be implemented next patch.

## Version 1.1.2
Released on 2022-10-30 22:00-07:00.
### Features
- Celestia now attaches any images that were present in an edited or deleted message in the message logs.
- The birthday patch will arrive in Version 1.2.0.
### Bug fixes
- Fixed a bug where Celestia inconsistently back-caches messages sent within the past hour upon reboot from a cache 
file.
- Fixed a bug where Celestia throws an error when attempting to write a log involving a post with over 1024 characters
in its body.
  - This might cause some logs affected by this scenario to look weird! Please let the devs know if any logs appear 
malformed or otherwise strange.
### Other changes
- Code format issues/QOL changes.
- After discussion with the mods, it has been determined that the current representation of stickers is sufficient and
therefore the dev team will not look back into putting stickers in picture form into logs.
### Known issues
- ~~It is possible for Celestia to repost the same log message multiple times by reacting to the same log message multiple
times.~~ **Addressed in Version 1.2.0.**
- At roughly 1am PDT on October 9, 2022, Celestia encountered a series of errors that ultimately resulted in Celestia
attempting to boot multiple instances of itself, EC2 booting up the test bot, and logs being in an untrustworthy state
from that time to roughly 8am of the same day due to the developers being asleep. The cause is currently believed to be
server-side or a connection issue, and is not an issue with the bot, but the devs are monitoring for this issue if it 
occurs in the future.

## Version 1.1.1
Released on 2022-09-26 17:14-07:00.
### Features
- Celestia now automatically reacts to all log and error messages with the "✉" (UTF-16 0x2709) emoji. If an admin
also reacts with the envelope, the message is copied into the Celestia channel. Note that this only works for log
messages sent since the most recent boot due to Discord limitations.
  - This change is aimed at making sharing issues with Celestia faster and easier. Working around the said limitation
is possible but, as of right now, it doesn't seem worth working around for now.
- Celestia now sends an attachment form of the "caught by celestia in 4k" sticker to users as opposed to a cryptic 
"Celestia is watching you..."
### Bug Fixes
None.
### Other changes
- Celestia now writes to a file instead of to console. This makes accessing what originally was console output
accessible even in the EC2 instance.
- The chance that Celestia sends the aforementioned image to a user upon an edit or delete has been increased from
1 in 500 to 1 in 100.
- Small code QOL changes.
### Known issues
- Celestia does not note the reply status of a message in the log entries; that is, right now it is impossible to look
at a log entry and know to which message a post was replying to, if applicable.

## Version 1.1.0
Released on 2022-09-18 16:18-07:00.
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
- Celestia now has a 1 in 500 probability of DMing a member a message when the user edits or deletes a message.
### Bug fixes
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
- ~~The dev team would also like to note that the updated sticker handling is still on the to-do list; it has not been
forgotten.~~ **Obsolete as of Version 1.1.2.**

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