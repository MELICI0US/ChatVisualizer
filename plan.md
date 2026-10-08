# The plan for what will need to change in the yapper

When we do this, we should add one or two parameters at a time and test it in a simulation first. This means we need to make sure the agent works with Jake's server first. 

### Group representation

The agent will have it's selected "community," but this should be separate from the groups that it chats with. 

Prioritize conversations?
- Ones with more of my community should get used more
- Maybe we also want to prioritize the people in my community and weigh conversations with them more

Keep track of active chats
- 


### Potential parameters

- threshold to break off from the larger group into a sub group



### Questions

Do we start with making an agent that can create groups at the right time (and ignore the chatting initially) or do we make an agent that can chat in group chats, but doesn't make them?

Do we need to start with something easier?
- focus just on managing group chats and not playing the game?
- focus just on playing the game and chatting, but not on group chats?

Can we do all of this with just an LLM?
- how do we validate it?
    - we can't really train it with the EPDM algorithm
    - maybe we could see if an analysis of the chat matches the internal action plan?



How I see it is we have two challenges we are trying to accomplish:
1) How do we combine strategy and language in a way that models human behavior as opposed to optimizing performance? (Mostly what Wyatt is working on)
2) How do we interact in concurrent group conversations? (What I am focusing on)

We need to disconnect the selected community from the chat groups. How do we represent this and how will it work?

Some things we could do to simplify this down into an easier task:
- Wizard of oz chatting based on the agent decisions (maybe we use this for the initial testing of the input)
- limit chats to one on one initially, and then try to address group chats
- use an LLM for full output (it decides what to send and who to send it to, I have some ideas for timing)


