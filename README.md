# telegram-marckbot2bot
Marckbot 2: Electric Boogaloo

A partial fork/copy/resurrection of Marckbot, a Telegram bot with a bunch of random useful features, including:
- `sed`-style `s/<regex>/<replacement>/<optional flags>` regex replacements
  - supported flags: `f` (only replace first), `i` (ignore case), `m` (multiline)
  - also supports using different characters than `/`, eg. `s#hello#world#` works too
- `/assign` command to assign messages (including media) to commands
  - reply to a message with `/assign <command>` and you can use `/command` to re-send that message
  - reply to another message `/reassign <command>` to change the command message
  - use `/unassign <command>` to remove the command
  - the `/defines` command can be used to list all assigned commands
- `/morejpeg` command for when an image just isn't JPEG enough
- `/bf` command to run Brainfuck code
  - reply `/bf` to a message to interpret it as Brainfuck
  - use `/bf <code>` to run code directly
- `/bonk` for when someone is horny on main
  - `/bonks` to list bonk count

Original bot by [Marckvdv](https://github.com/Marckvdv), improved by [pingiun](https://github.com/pingiun) and [InputUsername](https://github.com/InputUsername).
