<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ASKIANGELBOT - README</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 20px auto;
            padding: 0 15px;
            background-color: #f9f9f9;
        }
        h1, h2, h3 {
            color: #2c3e50;
        }
        h1 {
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            border-bottom: 1px solid #eee;
            padding-bottom: 5px;
        }
        .deploy-button {
            display: inline-block;
            margin: 20px 0;
        }
        code {
            background-color: #eee;
            padding: 2px 4px;
            border-radius: 4px;
        }
        pre {
            background-color: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            position: relative; /* For button positioning */
            margin-bottom: 10px; /* Space for buttons */
        }
        pre button {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 5px;
            cursor: pointer;
            position: absolute;
            top: 5px;
            right: 5px;
            font-size: 0.8em;
            opacity: 0.9;
            transition: opacity 0.2s;
        }
        pre button:hover {
            opacity: 1;
        }
        ul {
            list-style-type: disc;
            margin-left: 20px;
        }
        strong {
            color: #e74c3c; /* For warnings */
        }
        .command-block {
            background-color: #fff;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 10px;
            margin-bottom: 10px;
            position: relative;
        }
        .command-block button {
            background-color: #2ecc71; /* Green for copy buttons */
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 5px;
            cursor: pointer;
            float: right; /* Align to right */
            margin-left: 10px;
            font-size: 0.9em;
        }
        .command-block button:active {
            background-color: #27ae60;
        }
        .command-syntax {
            font-weight: bold;
            color: #34495e;
            display: inline-block; /* To allow button to float next to it */
        }
        .vip-emoji {
            font-size: 1.2em;
            vertical-align: middle;
        }
    </style>
</head>
<body>

    <h1>🚀 ASKIANGELBOT - आपका अपना स्मार्ट AI लर्निंग चैटबॉट 🚀</h1>

    <p><img src="https://user-images.githubusercontent.com/72007873/140228399-5f2c4a9f-5b7d-4c7b-b8c7-4d9d8b1c4e7c.gif" alt="ASKIANGELBOT - Live Animation"></p>
    <p>*(यह एक अस्थायी GIF है, आप अपने बॉट की वास्तविक एनिमेशन या एक अधिक प्रभावशाली AI/लर्निंग संबंधित GIF से इसे बदल सकते हैं!)*</p>

    <p>नमस्ते! मैं हूँ <strong>ASKIANGELBOT</strong>, आपकी अपनी पर्सनल AI लर्निंग और मॉडरेटर बॉट! मैं ग्रुप और प्राइवेट चैट्स में आपसे और दूसरों से सीखती हूँ, और समय के साथ और भी स्मार्ट होती जाती हूँ। मेरा मकसद आपकी बातचीत को मजेदार और ग्रुप को व्यवस्थित रखना है।</p>

    <p>मैं Telegram पर Python के Pyrogram फ्रेमवर्क और MongoDB डेटाबेस का उपयोग करके बनी हूँ।</p>

    <hr>

    <h2>✨ मुख्य विशेषताएँ (Features)</h2>
    <ul>
        <li><strong>🧠 सेल्फ-लर्निंग AI:</strong> मैं आपकी बातचीत से नए जवाब सीखती हूँ और समय के साथ बेहतर होती जाती हूँ।</li>
        <li><strong>💨 स्मार्ट कूलडाउन:</strong> अनचाहे स्पैम और मैसेज से बचाता हूँ, ताकि बातचीत स्मूथ रहे।</li>
        <li><strong>🔗 लिंक और मेंशन मॉडरेटर:</strong> ग्रुप एडमिन के लिए लिंक (नॉर्मल, बायो), और <code>@</code> मेंशन डिलीट करने की सुविधा।</li>
        <li><strong>🏆 एक्टिव यूजर लीडरबोर्ड:</strong> सबसे सक्रिय सदस्यों को पहचानता हूँ और पुरस्कार देता हूँ।</li>
        <li><strong>📊 विस्तृत स्टैटिस्टिक्स:</strong> बॉट के प्रदर्शन और डेटा के बारे में जानकारी देता हूँ।</li>
        <li><strong>🗑️ डेटा मैनेजमेंट:</strong> मैसेजेस, बटन्स और ट्रैकिंग डेटा को मैनेज और क्लियर करने के कमांड्स।</li>
        <li><strong>🔄 आसान रीस्टार्ट और ब्रॉडकास्ट:</strong> ओनर के लिए बॉट को रीस्टार्ट करने और सभी चैट्स पर मैसेज भेजने की सुविधा।</li>
        <li><strong>🛡️ ग्रुप कंट्रोल:</strong> ग्रुप में मेरी सक्रियता को ऑन/ऑफ करने का विकल्प।</li>
        <li><strong>🔔 नई यूजर सूचनाएं:</strong> जब कोई नया यूजर मुझे प्राइवेट में स्टार्ट करता है, तो ओनर को सूचित करता हूँ।</li>
    </ul>

    <hr>

    <h2>🛠️ डिप्लॉय करें अपना ASKIANGELBOT (Deploy Your Own ASKIANGELBOT)</h2>
    <p>अपना खुद का ASKIANGELBOT डिप्लॉय करना बहुत आसान है! बस नीचे दिए गए Koyeb बटन पर क्लिक करें और अपनी डिटेल्स भरें।</p>

    <p class="deploy-button">
        <a href="https://app.koyeb.com/deploy?name=chatbot-asbhai&repository=asbhaibsr%2FChatbot-asbhai&branch=main&run_command=python3+main.py&instance_type=free&regions=was&instances_min=0&autoscaling_sleep_idle_delay=300&env%5BAPI_HASH%5D=918e2aa94075a7d04717b371a21fb689&env%5BAPI_ID%5D=28762030&env%5BBOT_TOKEN%5D=8098449556%3AAAED8oT7U3lsPFwJxdxS-k0m27H3v9XC7EY&env%5BMONGO_URI_BUTTONS%5D=mongodb%2Bsrv%3A%2F%2Fed69yyr92n%3AkaY09k4z8zCjDSR3%40cluster0.6uhfmud.mongodb.net%2F%3FretryWrites%3Dtrue%26w%3Dmajority%26appName%3DCluster0&env%5BMONGO_URI_MESSAGES%5D=mongodb%2Bsrv%3A%2F%2Fjeriwo3420%3AsDz0ZevArtOnjpR0%40cluster0.yrfv26n.mongodb.net%2F%3FretryWrites%3Dtrue%26w%3Dmajority%26appName%3DCluster0&env%5BMONGO_URI_TRACKING%5D=mongodb%2Bsrv%3A%2F%2Fmockingbird07317%3ArTgIMbRuwlW7qMLq%40cluster0.4vlhect.mongodb.net%2F%3FretryWrites%3Dtrue%26w%3Dmajority%26appName%3DCluster0&env%5BOWNER_ID%5D=8019381468&ports=8080%3Bhttp%3B%2F&hc_protocol%5B8080%5D=tcp&hc_grace_period%5B8080%5D=5&hc_interval%5B8080%5D=30&hc_restart_limit%5B8080%5D=3&hc_timeout%5B8080%5D=5&hc_path%5B8080%5D=%2F&hc_method%5B8080%5D=get)" target="_blank">
            <img src="https://www.koyeb.com/static/images/deploy/button.svg" alt="Deploy to Koyeb">
        </a>
    </p>

    <h3>⚙️ आवश्यक पर्यावरण चर (Environment Variables)</h3>
    <p>यह बॉट ठीक से काम करने के लिए कुछ पर्यावरण चर (Environment Variables) पर निर्भर करता है। डिप्लॉय करते समय आपको इन्हें सेट करना होगा:</p>
    <ul>
        <li><code>BOT_TOKEN</code>: आपके बॉटफादर से प्राप्त बॉट टोकन।</li>
        <li><code>API_ID</code>: आपके My Telegram API से प्राप्त API ID।</li>
        <li><code>API_HASH</code>: आपके My Telegram API से प्राप्त API Hash।</li>
        <li><code>OWNER_ID</code>: आपका Telegram यूजर ID (न्यूमेरिक)। यह सुनिश्चित करेगा कि केवल आप ही संवेदनशील कमांड्स का उपयोग कर सकें।</li>
        <li><code>MONGO_URI_MESSAGES</code>: MongoDB Atlas कनेक्शन स्ट्रिंग आपके मैसेजेस डेटाबेस के लिए।</li>
        <li><code>MONGO_URI_BUTTONS</code>: MongoDB Atlas कनेक्शन स्ट्रिंग आपके बटन्स डेटाबेस के लिए।</li>
        <li><code>MONGO_URI_TRACKING</code>: MongoDB Atlas कनेक्शन स्ट्रिंग आपके ट्रैकिंग और यूजर डेटाबेस के लिए।</li>
    </ul>

    <p><strong>MongoDB डेटाबेस कैसे प्राप्त करें:</strong><br>
    आप <a href="https://www.mongodb.com/cloud/atlas" target="_blank">MongoDB Atlas</a> पर मुफ्त टियर अकाउंट बनाकर अपने तीनों MongoDB URI प्राप्त कर सकते हैं। तीन अलग-अलग क्लस्टर या कम से कम तीन अलग-अलग डेटाबेस बनाना सबसे अच्छा अभ्यास है।</p>

    <hr>

    <h2>🔑 कमांड्स (Commands)</h2>
    <p>यहाँ मेरे सभी कमांड्स की लिस्ट है:</p>

    <h3>🌟 सभी उपयोगकर्ताओं के लिए (For All Users)</h3>

    <div class="command-block">
        <span class="command-syntax"><code>/start</code></span> - बॉट से बातचीत शुरू करें।
        <button onclick="copyToClipboard('/start')">Copy</button>
    </div>

    <div class="command-block">
        <span class="command-syntax"><code>/help</code></span> - यह हेल्प मेनू देखें।
        <button onclick="copyToClipboard('/help')">Copy</button>
    </div>

    <div class="command-block">
        <span class="command-syntax"><code>/topusers</code></span> - सबसे सक्रिय उपयोगकर्ताओं का लीडरबोर्ड देखें और जानें कौन जीत रहा है! 💰
        <button onclick="copyToClipboard('/topusers')">Copy</button>
    </div>

    <div class="command-block">
        <span class="command-syntax"><code>/clearmydata</code></span> - आपकी सभी संग्रहित बातचीत (जो मैंने याद रखी हैं) और अर्निंग डेटा हटा दें।
        <button onclick="copyToClipboard('/clearmydata')">Copy</button>
    </div>

    <h3>👑 ग्रुप एडमिन्स और ओनर के लिए (For Group Admins & Owner)</h3>
    <p>ये कमांड्स ग्रुप चैट के लिए हैं और केवल ग्रुप एडमिनिस्ट्रेटर या ओनर द्वारा उपयोग की जा सकती हैं।</p>

    <div class="command-block">
        <span class="command-syntax"><code>/chat on/off</code></span> <span class="vip-emoji">⚡️</span> <strong>(ON/OFF)</strong><br>
        ग्रुप में बॉट की प्रतिक्रियाओं को <strong>चालू या बंद</strong> करें।
        <ul>
            <li><code>/chat on</code> <button onclick="copyToClipboard('/chat on')">Copy</button></li>
            <li><code>/chat off</code> <button onclick="copyToClipboard('/chat off')">Copy</button></li>
        </ul>
    </div>

    <div class="command-block">
        <span class="command-syntax"><code>/linkdel on/off</code></span> <span class="vip-emoji">🔗</span> <strong>(ON/OFF)</strong><br>
        ग्रुप में <strong>सभी प्रकार के लिंक्स</strong> (जैसे <code>http://</code>, <code>https://</code>, <code>www.</code>, <code>t.me/</code>) को <strong>डिलीट या अनुमति</strong> दें।
        <ul>
            <li><code>/linkdel on</code> <button onclick="copyToClipboard('/linkdel on')">Copy</button></li>
            <li><code>/linkdel off</code> <button onclick="copyToClipboard('/linkdel off')">Copy</button></li>
        </ul>
    </div>

    <div class="command-block">
        <span class="command-syntax"><code>/biolinkdel on/off</code></span> <span class="vip-emoji">👤🔗</span> <strong>(ON/OFF)</strong><br>
        उन उपयोगकर्ताओं के मैसेजेस को <strong>डिलीट या अनुमति</strong> दें जिनकी Telegram बायो में <code>t.me</code> या <code>http/https</code> लिंक्स हैं।
        <ul>
            <li><code>/biolinkdel on</code> <button onclick="copyToClipboard('/biolinkdel on')">Copy</button></li>
            <li><code>/biolinkdel off</code> <button onclick="copyToClipboard('/biolinkdel off')">Copy</button></li>
        </ul>
    </div>

    <div class="command-block">
        <span class="command-syntax"><code>/biolink &lt;userid&gt;</code></span> <span class="vip-emoji">➕</span><br>
        एक विशिष्ट यूजर को <strong>बायो में लिंक्स रखने की छूट</strong> दें, भले ही <code>biolinkdel</code> ऑन हो। इसे हटाने के लिए <code>/biolink remove &lt;userid&gt;</code> का उपयोग करें।
        <ul>
            <li><code>/biolink 123456789</code> <button onclick="copyToClipboard('/biolink 123456789')">Copy</button></li>
            <li><code>/biolink remove 123456789</code> <button onclick="copyToClipboard('/biolink remove 123456789')">Copy</button></li>
        </ul>
    </div>

    <div class="command-block">
        <span class="command-syntax"><code>/usernamedel on/off</code></span> <span class="vip-emoji">@</span> <strong>(ON/OFF)</strong><br>
        ग्रुप में <code>@</code> <strong>मेंशन वाले मैसेजेस को डिलीट या अनुमति</strong> दें।
        <ul>
            <li><code>/usernamedel on</code> <button onclick="copyToClipboard('/usernamedel on')">Copy</button></li>
            <li><code>/usernamedel off</code> <button onclick="copyToClipboard('/usernamedel off')">Copy</button></li>
        </ul>
    </div>

    <h3>🎩 केवल बॉट ओनर के लिए (Owner Only Commands)</h3>
    <p>ये कमांड्स केवल बॉट के <code>OWNER_ID</code> द्वारा ही उपयोग की जा सकती हैं और आमतौर पर प्राइवेट चैट में उपयोग की जाती हैं।</p>

    <div class="command-block">
        <span class="command-syntax"><code>/groups</code></span> - उन सभी ग्रुप्स की सूची देखें जिनमें बॉट शामिल है।
        <button onclick="copyToClipboard('/groups')">Copy</button>
    </div>

    <div class="command-block">
        <span class="command-syntax"><code>/stats check</code></span> - बॉट के कुल संदेशों, उपयोगकर्ताओं और ग्रुप्स के आंकड़े देखें।
        <button onclick="copyToClipboard('/stats check')">Copy</button>
    </div>

    <div class="command-block">
        <span class="command-syntax"><code>/cleardata &lt;percentage&gt;</code></span> - डेटाबेस से निश्चित प्रतिशत में पुराने मैसेजेस डिलीट करें।
        <ul>
            <li>उदाहरण: <code>/cleardata 30%</code> <button onclick="copyToClipboard('/cleardata 30%')">Copy</button></li>
        </ul>
    </div>

    <div class="command-block">
        <span class="command-syntax"><code>/deletemessage &lt;content/sticker_id&gt;</code></span> - विशिष्ट टेक्स्ट या स्टिकर ID के सभी मैसेजेस को डेटाबेस से डिलीट करें।
        <ul>
            <li>उदाहरण: <code>/deletemessage हेलो</code> <button onclick="copyToClipboard('/deletemessage हेलो')">Copy</button></li>
            <li>उदाहरण: <code>/deletemessage BQADAgAD0QAD0QJ9GgACyJt4b2l_</code> (स्टिकर ID) <button onclick="copyToClipboard('/deletemessage BQADAgAD0QAD0QJ9GgACyJt4b2l_')">Copy</button></li>
        </ul>
    </div>

    <div class="command-block">
        <span class="command-syntax"><code>/clearearning</code></span> - सभी उपयोगकर्ताओं के अर्निंग डेटा (संदेश गणना) को रीसेट करें।
        <button onclick="copyToClipboard('/clearearning')">Copy</button>
    </div>

    <div class="command-block">
        <span class="command-syntax"><code>/clearall</code></span> <span class="vip-emoji">⚠️</span> - <strong>अत्यधिक महत्वपूर्ण!</strong> सभी तीन डेटाबेस (<code>messages</code>, <code>buttons</code>, <code>tracking</code>) से <strong>सारा डेटा स्थायी रूप से डिलीट करें</strong>। उपयोग करने से पहले पुष्टि करनी होगी।
        <button onclick="copyToClipboard('/clearall')">Copy</button>
    </div>

    <div class="command-block">
        <span class="command-syntax"><code>/leavegroup &lt;group_id&gt;</code></span> - बॉट को एक विशिष्ट ग्रुप से बाहर निकालें और उस ग्रुप से संबंधित डेटा हटा दें।
        <ul>
            <li>उदाहरण: <code>/leavegroup -1001234567890</code> <button onclick="copyToClipboard('/leavegroup -1001234567890')">Copy</button></li>
        </ul>
    </div>

    <div class="command-block">
        <span class="command-syntax"><code>/broadcast &lt;message&gt;</code></span> - सभी ग्रुप्स और प्राइवेट चैट्स पर एक संदेश भेजें।
        <ul>
            <li>उदाहरण: <code>/broadcast यह एक घोषणा है!</code> <button onclick="copyToClipboard('/broadcast यह एक घोषणा है!')">Copy</button></li>
        </ul>
    </div>

    <div class="command-block">
        <span class="command-syntax"><code>/restart</code></span> - बॉट को रीस्टार्ट करें।
        <button onclick="copyToClipboard('/restart')">Copy</button>
    </div>

    <hr>

    <h2>🤝 योगदान (Contributions)</h2>
    <p>यह प्रोजेक्ट ओपन-सोर्स है और आपके योगदान का हमेशा स्वागत है! अगर आप इस बॉट को और बेहतर बनाने के लिए कोई विचार या सुधार चाहते हैं, तो बेझिझक <strong>फ़ोर्क करें</strong>, कोड में बदलाव करें और एक <strong>पुल रिक्वेस्ट (Pull Request)</strong> सबमिट करें।</p>
    <ul>
        <li><a href="https://github.com/asbhaibsr/Chatbot-asbhai.git" target="_blank">GitHub Repository</a></li>
    </ul>

    <hr>

    <h2>❤️ क्रेडिट्स और संपर्क (Credits & Contact)</h2>
    <p>यह अद्भुत बॉट <strong>@asbhaibsr</strong> द्वारा बनाया और डिज़ाइन किया गया है।</p>
    <ul>
        <li><strong>👨‍💻 बॉट डेवलपर:</strong> <a href="https://t.me/asbhaibsr" target="_blank">@asbhaibsr</a></li>
        <li><strong>📣 अपडेट चैनल:</strong> <a href="https://t.me/asbhai_bsr" target="_blank">@asbhai_bsr</a></li>
        <li><strong>❓ सपोर्ट ग्रुप:</strong> <a href="https://t.me/aschat_group" target="_blank">@aschat_group</a></li>
    </ul>
    <p>अगर आपको कोई सहायता चाहिए, कोई बग मिला है, या बस हाय कहना चाहते हैं, तो ऊपर दिए गए लिंक्स के माध्यम से संपर्क करें।</p>

    <hr>

    <p><strong>यह बॉट @asbhaibsr की संपत्ति है। अनधिकृत फ़ोर्किंग, रीब्रांडिंग, या रीसेलिंग सख्ती से प्रतिबंधित है।</strong></p>

    <script>
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(function() {
                alert('Copied to clipboard!');
            }, function(err) {
                console.error('Could not copy text: ', err);
                alert('Failed to copy. Please copy manually.');
            });
        }
    </script>

</body>
</html>
