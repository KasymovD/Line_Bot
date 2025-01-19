var ACCESS_CODE = "1234";

function doPost(e) {
  try {
    var json = JSON.parse(e.postData.contents);

    
    var LINE_ACCESS_TOKEN = "";

    
    var userMessage = json.events[0].message.text;
    var replyToken = json.events[0].replyToken;

    
    if (userMessage === "Начать") {
      
      sendTextMessage(replyToken, LINE_ACCESS_TOKEN, "Добро пожаловать! Пожалуйста, введите код для продолжения.");
    } else if (userMessage === ACCESS_CODE) {
      
      sendTextMessage(replyToken, LINE_ACCESS_TOKEN, "Код принят! Что бы вы хотели сделать?");
      
    } else {
      
      sendTextMessage(replyToken, LINE_ACCESS_TOKEN, "Неверный код. Попробуйте снова.");
    }

    return ContentService.createTextOutput(JSON.stringify({status: "ok"})).setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    Logger.log("Ошибка в doPost: " + error);
    return ContentService.createTextOutput(JSON.stringify({status: "error"})).setMimeType(ContentService.MimeType.JSON);
  }
}

function sendTextMessage(replyToken, token, text) {
  try {
    var replyMessage = {
      replyToken: replyToken,
      messages: [{
        "type": "text",
        "text": text
      }]
    };

    UrlFetchApp.fetch("https://api.line.me/v2/bot/message/reply", {
      "method": "post",
      "contentType": "application/json",
      "headers": {
        "Authorization": "Bearer " + token
      },
      "payload": JSON.stringify(replyMessage)
    });
  } catch (error) {
    Logger.log("Ошибка отправки текста: " + error);
  }
}
