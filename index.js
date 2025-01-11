require('dotenv').config();
const line = require('@line/bot-sdk');
const express = require('express');
const axios = require('axios');

const config = {
  channelAccessToken: process.env.CHANNEL_ACCESS_TOKEN,
  channelSecret: process.env.CHANNEL_SECRET
};

const app = express();

app.post('/webhook', line.middleware(config), (req, res) => {
  Promise
    .all(req.body.events.map(handleEvent))
    .then((result) => res.json(result))
    .catch((err) => {
      console.error(err);
      res.status(500).end();
    });
});

const client = new line.Client(config);

async function handleEvent(event) {
  if (event.type !== 'message' || event.message.type !== 'text') {
    return Promise.resolve(null);
  }

  const userMessage = event.message.text.trim();
  const parsedCommand = parseCommand(userMessage);

  if (parsedCommand) {
    const { command, args } = parsedCommand;

    switch (command) {
      case '/translate':
        return handleTranslateCommand(event, args);
      case '/weather':
        return handleWeatherCommand(event, args);
      case '/news':
        return handleNewsCommand(event, args);
      case '/stock':
        return handleStockCommand(event, args);
      case '/help':
        return handleHelpCommand(event);
      default:
        return handleUnknownCommand(event);
    }
  } else {
    const echo = { 
      type: 'text', 
      text: `Вы написали: ${userMessage}` 
    };
    return client.replyMessage(event.replyToken, echo);
  }
}

function parseCommand(message) {
  const parts = message.split(' ');
  const command = parts[0].toLowerCase();

  if (command === '/translate') {
    if (parts.length < 3) {
      return { command, args: null };
    }
    const targetLang = parts[1];
    const textToTranslate = parts.slice(2).join(' ');
    return { command, args: { targetLang, textToTranslate } };
  }

  if (command === '/weather') {
    if (parts.length < 2) {
      return { command, args: null };
    }
    const location = parts.slice(1).join(' ');
    return { command, args: { location } };
  }

  if (command === '/news') {
    return { command, args: null };
  }

  if (command === '/stock') {
    if (parts.length < 2) {
      return { command, args: null };
    }
    const symbol = parts[1].toUpperCase();
    return { command, args: { symbol } };
  }

  if (command === '/help') {
    return { command, args: null };
  }

  return null;
}

async function handleTranslateCommand(event, args) {
  if (!args || !args.targetLang || !args.textToTranslate) {
    const response = { 
      type: 'text', 
      text: 'Использование: /translate <язык> <текст для перевода>'
    };
    return client.replyMessage(event.replyToken, response);
  }

  try {
    const translatedText = await translateText(args.textToTranslate, args.targetLang);
    const response = { 
      type: 'text', 
      text: `Перевод (${args.targetLang}): ${translatedText}` 
    };
    return client.replyMessage(event.replyToken, response);
  } catch (error) {
    const response = { 
      type: 'text', 
      text: 'Ошибка при переводе.' 
    };
    return client.replyMessage(event.replyToken, response);
  }
}

async function translateText(text, targetLang) {
  const apiKey = process.env.GOOGLE_TRANSLATE_API_KEY;
  const url = `https://translation.googleapis.com/language/translate/v2`;
  const response = await axios.post(url, null, {
    params: {
      q: text,
      target: targetLang,
      key: apiKey
    }
  });

  if (response.data && response.data.data && response.data.data.translations[0]) {
    return response.data.data.translations[0].translatedText;
  } else {
    throw new Error('Неверный ответ от API перевода');
  }
}

async function handleWeatherCommand(event, args) {
  if (!args || !args.location) {
    const response = { 
      type: 'text', 
      text: 'Использование: /weather <место>'
    };
    return client.replyMessage(event.replyToken, response);
  }

  try {
    const weatherInfo = await getWeather(args.location);
    const response = { 
      type: 'text', 
      text: `Погода в ${args.location}: ${weatherInfo}` 
    };
    return client.replyMessage(event.replyToken, response);
  } catch (error) {
    const response = { 
      type: 'text', 
      text: 'Ошибка при получении погоды.' 
    };
    return client.replyMessage(event.replyToken, response);
  }
}

async function getWeather(location) {
  const apiKey = process.env.OPENWEATHER_API_KEY;
  const url = `https://api.openweathermap.org/data/2.5/weather`;
  const response = await axios.get(url, {
    params: {
      q: location,
      appid: apiKey,
      units: 'metric',
      lang: 'ru'
    }
  });

  if (response.data) {
    const temp = response.data.main.temp;
    const description = response.data.weather[0].description;
    return `${temp}°C, ${description}`;
  } else {
    throw new Error('Неверный ответ от API погоды');
  }
}

async function handleNewsCommand(event, args) {
  try {
    const news = await getNews();
    const response = { 
      type: 'text', 
      text: news 
    };
    return client.replyMessage(event.replyToken, response);
  } catch (error) {
    const response = { 
      type: 'text', 
      text: 'Ошибка при получении новостей.' 
    };
    return client.replyMessage(event.replyToken, response);
  }
}

async function getNews() {
  const apiKey = process.env.NEWS_API_KEY;
  const url = `https://newsapi.org/v2/top-headlines`;
  const response = await axios.get(url, {
    params: {
      country: 'ru',
      apiKey: apiKey
    }
  });

  if (response.data && response.data.articles) {
    const articles = response.data.articles.slice(0, 5);
    return articles.map((article, index) => `${index + 1}. ${article.title}`).join('\n');
  } else {
    throw new Error('Неверный ответ от API новостей');
  }
}

async function handleStockCommand(event, args) {
  if (!args || !args.symbol) {
    const response = { 
      type: 'text', 
      text: 'Использование: /stock <тикер>'
    };
    return client.replyMessage(event.replyToken, response);
  }

  try {
    const stockInfo = await getStock(args.symbol);
    const response = { 
      type: 'text', 
      text: `Акция ${args.symbol}: ${stockInfo}` 
    };
    return client.replyMessage(event.replyToken, response);
  } catch (error) {
    const response = { 
      type: 'text', 
      text: 'Ошибка при получении информации о акции.' 
    };
    return client.replyMessage(event.replyToken, response);
  }
}

async function getStock(symbol) {
  const apiKey = process.env.ALPHA_VANTAGE_API_KEY;
  const url = `https://www.alphavantage.co/query`;
  const response = await axios.get(url, {
    params: {
      function: 'GLOBAL_QUOTE',
      symbol: symbol,
      apikey: apiKey
    }
  });

  if (response.data && response.data['Global Quote']) {
    const price = response.data['Global Quote']['05. price'];
    const change = response.data['Global Quote']['09. change'];
    return `Текущая цена: $${price}, Изменение: ${change}`;
  } else {
    throw new Error('Неверный ответ от API акций');
  }
}

function handleHelpCommand(event) {
  const helpText = `
Доступные команды:
/translate <язык> <текст> - Перевести текст на указанный язык.
/weather <место> - Получить погоду в указанном месте.
/news - Получить последние новости.
/stock <тикер> - Получить информацию о акции.
/help - Показать это сообщение.
  `;
  const response = { 
    type: 'text', 
    text: helpText 
  };
  return client.replyMessage(event.replyToken, response);
}

function handleUnknownCommand(event) {
  const response = { 
    type: 'text', 
    text: 'Неизвестная команда. Введите /help для списка доступных команд.' 
  };
  return client.replyMessage(event.replyToken, response);
}

const port = process.env.PORT || 3000;
app.listen(port, () => {
  console.log(`LINE Bot запущен на порту ${port}`);
});
