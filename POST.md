every ai writing tool sounds the same. i finally worked out why.

the model has no idea who you are. so it writes the average of everyone it ever read, and that average reads like a press release. every time.

"sound more human" doesn't fix it. there's no general human voice to aim at. there's only mine, and the model has never seen it.

except it has. i've been typing at it for months.

so i built being-human. it reads the prompts i'd already written and measures how i actually write, then hands that back as instructions with numbers attached. not "be concise". "your median message is 12 words". not "vary your sentences" but "you average 9 words and swing to 81, so stop writing every line the same length".

two things came out of it that i haven't seen elsewhere.

first: my history has both sides of the conversation. so every word can be scored by how much more likely i am to use it than the model is, same topics, same threads. top of that list is my voice. bottom is the model's. that's the whole trick. mine came back: actually, clean, rather, genuinely, exactly, roughly. none of those appear on any published list of ai words. that's just what this model does when talking to me.

second took three tries. every tool here builds a profile, then asks you to eyeball whether the output sounds right. eyeballing fails. always. a draft reads fine to whoever just read the instructions that made it. so instead: among things i actually wrote, at this length, how unusual is this text? that's burrows's delta, scored against 400 same-length chunks of my own writing.

my first version was backwards. bland generic prose landed closer to my centre than my own writing did, which is the exact opposite of what the thing is for. slop won. the fix was resampling the comparison set at the draft's exact length, which sounds small and took two rewrites. now held-out chunks of my real writing sit at the 49th to 60th percentile, where they belong.

and here's the bit i actually like.

i wrote the first draft of this post in default assistant voice. it scored 31. that draft also sailed through the authorship check at the 30th percentile, because bland grammar is unremarkable grammar and nothing there looked foreign. only the slop filter caught it.

that gap is the whole argument for two checks. a readme written by someone else scores 97 for cleanliness and 94th percentile for "not you". good writing, no tells, wrong person. neither test catches both failures alone.

this version scores 100. it took four passes, and the tool named the fix each time.

inside-lago, slop-guard, idiolect and writer-persona all got somewhere before me. writer-persona's backtest is where the validation idea came from. mine is the deterministic version: no llm judge, no api calls, same answer every time.

runs locally, stdlib python, no dependencies, nothing leaves my machine. claude code skill or an mcp server for chatgpt, cursor, codex, zed. MIT.

github.com/Syedomershah99/being-human

* written by being-human
