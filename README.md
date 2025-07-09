# 🚀 ASKIANGELBOT - आपका अपना स्मार्ट AI लर्निंग चैटबॉट 🚀

![ASKIANGELBOT - Live Animation](https://user-images.githubusercontent.com/72007873/140228399-5f2c4a9f-5b7d-4c7b-b8c7-4d9d8b1c4e7c.gif)
*(यह एक अस्थायी GIF है, आप अपने बॉट की वास्तविक एनिमेशन या एक अधिक प्रभावशाली AI/लर्निंग संबंधित GIF से इसे बदल सकते हैं!)*

नमस्ते! मैं हूँ **ASKIANGELBOT**, आपकी अपनी पर्सनल AI लर्निंग और मॉडरेटर बॉट! मैं ग्रुप और प्राइवेट चैट्स में आपसे और दूसरों से सीखती हूँ, और समय के साथ और भी स्मार्ट होती जाती हूँ। मेरा मकसद आपकी बातचीत को मजेदार और ग्रुप को व्यवस्थित रखना है।

मैं Telegram पर Python के Pyrogram फ्रेमवर्क और MongoDB डेटाबेस का उपयोग करके बनी हूँ।

---

## ✨ मुख्य विशेषताएँ (Features)

* **🧠 सेल्फ-लर्निंग AI:** मैं आपकी बातचीत से नए जवाब सीखती हूँ और समय के साथ बेहतर होती जाती हूँ।
* **💨 स्मार्ट कूलडाउन:** अनचाहे स्पैम और मैसेज से बचाता हूँ, ताकि बातचीत स्मूथ रहे।
* **🔗 लिंक और मेंशन मॉडरेटर:** ग्रुप एडमिन के लिए लिंक (नॉर्मल, बायो), और `@` मेंशन डिलीट करने की सुविधा।
* **🏆 एक्टिव यूजर लीडरबोर्ड:** सबसे सक्रिय सदस्यों को पहचानता हूँ और पुरस्कार देता हूँ।
* **📊 विस्तृत स्टैटिस्टिक्स:** बॉट के प्रदर्शन और डेटा के बारे में जानकारी देता हूँ।
* **🗑️ डेटा मैनेजमेंट:** मैसेजेस, बटन्स और ट्रैकिंग डेटा को मैनेज और क्लियर करने के कमांड्स।
* **🔄 आसान रीस्टार्ट और ब्रॉडकास्ट:** ओनर के लिए बॉट को रीस्टार्ट करने और सभी चैट्स पर मैसेज भेजने की सुविधा।
* **🛡️ ग्रुप कंट्रोल:** ग्रुप में मेरी सक्रियता को ऑन/ऑफ करने का विकल्प।
* **🔔 नई यूजर सूचनाएं:** जब कोई नया यूजर मुझे प्राइवेट में स्टार्ट करता है, तो ओनर को सूचित करता हूँ।

---

## 🛠️ डिप्लॉय करें अपना ASKIANGELBOT (Deploy Your Own ASKIANGELBOT)

अपना खुद का ASKIANGELBOT डिप्लॉय करना बहुत आसान है! बस नीचे दिए गए Koyeb बटन पर क्लिक करें और अपनी डिटेल्स भरें।

[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?name=chatbot-asbhai&repository=asbhaibsr%2FChatbot-asbhai&branch=main&run_command=python3+main.py&instance_type=free&regions=was&instances_min=0&autoscaling_sleep_idle_delay=300&env%5BAPI_HASH%5D=918e2aa94075a7d04717b371a21fb689&env%5BAPI_ID%5D=28762030&env%5BBOT_TOKEN%5D=8098449556%3AAAED8oT7U3lsPFwJxdxS-k0m27H3v9XC7EY&env%5BMONGO_URI_BUTTONS%5D=mongodb%2Bsrv%3A%2F%2Fed69yyr92n%3AkaY09k4z8zCjDSR3%40cluster0.6uhfmud.mongodb.net%2F%3FretryWrites%3Dtrue%26w%3Dmajority%26appName%3DCluster0&env%5BMONGO_URI_MESSAGES%5D=mongodb%2Bsrv%3A%2F%2Fjeriwo3420%3AsDz0ZevArtOnjpR0%40cluster0.yrfv26n.mongodb.net%2F%3FretryWrites%3Dtrue%26w%3Dmajority%26appName%3DCluster0&env%5BMONGO_URI_TRACKING%5D=mongodb%2Bsrv%3A%2F%2Fmockingbird07317%3ArTgIMbRuwlW7qMLq%40cluster0.4vlhect.mongodb.net%2F%3FretryWrites%3Dtrue%26w%3Dmajority%26appName%3DCluster0&env%5BOWNER_ID%5D=8019381468&ports=8080%3Bhttp%3B%2F&hc_protocol%5B8080%5D=tcp&hc_grace_period%5B8080%5D=5&hc_interval%5B8080%5D=30&hc_restart_limit%5B8080%5D=3&hc_timeout%5B8080%5D=5&hc_path%5B8080%5D=%2F&hc_method%5B8080%5D=get)

### ⚙️ आवश्यक पर्यावरण चर (Environment Variables)

यह बॉट ठीक से काम करने के लिए कुछ पर्यावरण चर (Environment Variables) पर निर्भर करता है। डिप्लॉय करते समय आपको इन्हें सेट करना होगा:

* `BOT_TOKEN`: आपके बॉटफादर से प्राप्त बॉट टोकन।
* `API_ID`: आपके My Telegram API से प्राप्त API ID।
* `API_HASH`: आपके My Telegram API से प्राप्त API Hash।
* `OWNER_ID`: आपका Telegram यूजर ID (न्यूमेरिक)। यह सुनिश्चित करेगा कि केवल आप ही संवेदनशील कमांड्स का उपयोग कर सकें।
* `MONGO_URI_MESSAGES`: MongoDB Atlas कनेक्शन स्ट्रिंग आपके मैसेजेस डेटाबेस के लिए।
* `MONGO_URI_BUTTONS`: MongoDB Atlas कनेक्शन स्ट्रिंग आपके बटन्स डेटाबेस के लिए।
* `MONGO_URI_TRACKING`: MongoDB Atlas कनेक्शन स्ट्रिंग आपके ट्रैकिंग और यूजर डेटाबेस के लिए।

**MongoDB डेटाबेस कैसे प्राप्त करें:**
आप [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) पर मुफ्त टियर अकाउंट बनाकर अपने तीनों MongoDB URI प्राप्त कर सकते हैं। तीन अलग-अलग क्लस्टर या कम से कम तीन अलग-अलग डेटाबेस बनाना सबसे अच्छा अभ्यास है।

---

## 🔑 कमांड्स (Commands)

यहाँ मेरे सभी कमांड्स की लिस्ट है:

### 🌟 सभी उपयोगकर्ताओं के लिए (For All Users)

* `/start` - बॉट से बातचीत शुरू करें।
* `/help` - यह हेल्प मेनू देखें।
* `/topusers` - सबसे सक्रिय उपयोगकर्ताओं का लीडरबोर्ड देखें और जानें कौन जीत रहा है! 💰
* `/clearmydata` - आपकी सभी संग्रहित बातचीत (जो मैंने याद रखी हैं) और अर्निंग डेटा हटा दें।

### 👑 ग्रुप एडमिन्स और ओनर के लिए (For Group Admins & Owner)

ये कमांड्स ग्रुप चैट के लिए हैं और केवल ग्रुप एडमिनिस्ट्रेटर या ओनर द्वारा उपयोग की जा सकती हैं।

* `/chat on/off` ⚡️ **(ON/OFF)** - ग्रुप में बॉट की प्रतिक्रियाओं को **चालू या बंद** करें।
    * `/chat on`
    * `/chat off`

* `/linkdel on/off` 🔗 **(ON/OFF)** - ग्रुप में **सभी प्रकार के लिंक्स** (जैसे `http://`, `https://`, `www.`, `t.me/`) को **डिलीट या अनुमति** दें।
    * `/linkdel on`
    * `/linkdel off`

* `/biolinkdel on/off` 👤🔗 **(ON/OFF)** - उन उपयोगकर्ताओं के मैसेजेस को **डिलीट या अनुमति** दें जिनकी Telegram बायो में `t.me` या `http/https` लिंक्स हैं।
    * `/biolinkdel on`
    * `/biolinkdel off`

* `/biolink <userid>` ➕ - एक विशिष्ट यूजर को **बायो में लिंक्स रखने की छूट** दें, भले ही `biolinkdel` ऑन हो। इसे हटाने के लिए `/biolink remove <userid>` का उपयोग करें।
    * `/biolink 123456789`
    * `/biolink remove 123456789`

* `/usernamedel on/off` @ **(ON/OFF)** - ग्रुप में `@` **मेंशन वाले मैसेजेस को डिलीट या अनुमति** दें।
    * `/usernamedel on`
    * `/usernamedel off`

### 🎩 केवल बॉट ओनर के लिए (Owner Only Commands)

ये कमांड्स केवल बॉट के `OWNER_ID` द्वारा ही उपयोग की जा सकती हैं और आमतौर पर प्राइवेट चैट में उपयोग की जाती हैं।

* `/groups` - उन सभी ग्रुप्स की सूची देखें जिनमें बॉट शामिल है।
* `/stats check` - बॉट के कुल संदेशों, उपयोगकर्ताओं और ग्रुप्स के आंकड़े देखें।
* `/cleardata <percentage>` - डेटाबेस से निश्चित प्रतिशत में पुराने मैसेजेस डिलीट करें (जैसे `/cleardata 30%`)।
* `/deletemessage <content/sticker_id>` - विशिष्ट टेक्स्ट या स्टिकर ID के सभी मैसेजेस को डेटाबेस से डिलीट करें।
    * उदाहरण: `/deletemessage हेलो`
    * उदाहरण: `/deletemessage BQADAgAD0QAD0QJ9GgACyJt4b2l_` (स्टिकर ID)
* `/clearearning` - सभी उपयोगकर्ताओं के अर्निंग डेटा (संदेश गणना) को रीसेट करें।
* `/clearall` ⚠️ - **अत्यधिक महत्वपूर्ण!** सभी तीन डेटाबेस (`messages`, `buttons`, `tracking`) से **सारा डेटा स्थायी रूप से डिलीट करें**। उपयोग करने से पहले पुष्टि करनी होगी।
* `/leavegroup <group_id>` - बॉट को एक विशिष्ट ग्रुप से बाहर निकालें और उस ग्रुप से संबंधित डेटा हटा दें।
* `/broadcast <message>` - सभी ग्रुप्स और प्राइवेट चैट्स पर एक संदेश भेजें।
* `/restart` - बॉट को रीस्टार्ट करें।

---

## 🤝 योगदान (Contributions)

यह प्रोजेक्ट ओपन-सोर्स है और आपके योगदान का हमेशा स्वागत है! अगर आप इस बॉट को और बेहतर बनाने के लिए कोई विचार या सुधार चाहते हैं, तो बेझिझक **फ़oर्क करें**, कोड में बदलाव करें और एक **पुल रिक्वेस्ट (Pull Request)** सबमिट करें।

* [GitHub Repository](https://github.com/asbhaibsr/Chatbot-asbhai.git)

---

## ❤️ क्रेडिट्स और संपर्क (Credits & Contact)

यह अद्भुत बॉट **@asbhaibsr** द्वारा बनाया और डिज़ाइन किया गया है।

* **👨‍💻 बॉट डेवलपर:** [@asbhaibsr](https://t.me/asbhaibsr)
* **📣 अपडेट चैनल:** [@asbhai_bsr](https://t.me/asbhai_bsr)
* **❓ सपोर्ट ग्रुप:** [@aschat_group](https://t.me/aschat_group)

अगर आपको कोई सहायता चाहिए, कोई बग मिला है, या बस हाय कहना चाहते हैं, तो ऊपर दिए गए लिंक्स के माध्यम से संपर्क करें।

---

**यह बॉट @asbhaibsr की संपत्ति है। अनधिकृत फ़ोर्किंग, रीब्रांडिंग, या रीसेलिंग सख्ती से प्रतिबंधित है।**
