every ai writing tool sounds the same. i finally worked out why.

the model has no idea who you are. so it writes the average of everyone it ever read, and that average reads like a press release.

"sound more human" doesn't fix it. there's no general human voice to aim at. there's only mine, and the model has never seen it.

except it has. i've been typing at it for months.

so i built being-human. it reads the prompts i'd already written, measures how i actually write, and hands that back as instructions with numbers attached. not "be concise". "your median message is 12 words".

the part i didn't expect: my history holds both sides of the conversation. so every word can be scored by how much more likely i am to use it than the model is, same topics, same threads. top of that list is my voice. bottom is the model's. mine came back: actually, clean, rather, genuinely, exactly, roughly. none of those sit on any published list of ai words. that's just what this model does when talking to me.

then it checks a draft twice. once for ai tells. once for whether the writing is statistically mine at all.

i wrote the first version of this post in default assistant voice. it scored 31. it also passed the authorship check, because bland grammar is unremarkable grammar and nothing there looked foreign. only the slop filter caught it. that gap is why there are two.

this version scores 100. four passes, and the tool named the fix each time.

runs locally. stdlib python, no dependencies, nothing leaves my machine. claude code skill, or an mcp server for chatgpt, cursor, codex, zed. MIT.

inside-lago, slop-guard, idiolect and writer-persona got here before me. writer-persona's backtest is where the validation idea came from.

github.com/Syedomershah99/being-human

* written by being-human
