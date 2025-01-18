'use strict';

require('dotenv').config();

const express = require('express');
const bodyParser = require('body-parser');
const line = require('@line/bot-sdk');

const app = express();

const config = {
  channelAccessToken: process.env.CHANNEL_ACCESS_TOKEN,
  channelSecret: process.env.CHANNEL_SECRET
};

const client = new line.Client(config);

app.use(bodyParser.json());

app.post('/webhook', line.middleware(config), (req, res) => {
  Promise
    .all(req.body.events.map(handleEvent))
    .then((result) => res.json(result))
    .catch((error) => {
      console.error('Error handling events:', error);
      res.status(500).end();
    });
});

function handleEvent(event) {
  if (event.type !== 'message' || event.message.type !== 'text') {
    return Promise.resolve(null);
  }

  const echo = { type: 'text', text: `You said: ${event.message.text}` };

  return client.replyMessage(event.replyToken, echo);
}

app.get('/', (req, res) => {
  res.send('Hello, LINE Bot is running!');
});

const port = process.env.PORT || 3000;
app.listen(port, () => {
  console.log(`LINE Bot server running on port ${port}`);
});
