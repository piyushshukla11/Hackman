/**
 * generate-500-voyage-reviews.js
 * Generates exactly 500 realistic, high-quality reviews across all 5 platforms:
 * - Amazon: 100 reviews (25 Headphones, 25 Mic, 25 Mouse, 25 Monitor)
 * - Flipkart: 100 reviews (25 Headphones, 25 Mic, 25 Mouse, 25 Monitor)
 * - JioMart: 100 reviews (25 Headphones, 25 Mic, 25 Mouse, 25 Monitor)
 * - Voyage Brand Store: 100 reviews (25 Headphones, 25 Mic, 25 Mouse, 25 Monitor)
 * - Steam: 100 reviews (25 BG3, 25 Wukong, 25 Cyberpunk, 25 Elden Ring)
 * Total: Exactly 500 reviews across all platforms.
 */

const fs = require('fs');
const path = require('path');

const PRODUCTS = {
  prod_001: { name: 'Voyage Horizon ANC', category: 'Headphones', item: 'headphones' },
  prod_002: { name: 'Voyage StreamCast Pro', category: 'Microphones', item: 'mic' },
  prod_003: { name: 'Voyage Apex Wireless', category: 'Gaming Mouse', item: 'mouse' },
  prod_004: { name: 'Voyage UltraVision 27"', category: 'Gaming Monitors', item: 'monitor' },
};

const STEAM_GAMES = {
  prod_001: { name: "Baldur's Gate 3", hoursMin: 60, hoursMax: 240, genre: 'RPG' },
  prod_002: { name: 'Black Myth: Wukong', hoursMin: 35, hoursMax: 130, genre: 'Action RPG' },
  prod_003: { name: 'Cyberpunk 2077', hoursMin: 50, hoursMax: 280, genre: 'Open World RPG' },
  prod_004: { name: 'Elden Ring', hoursMin: 70, hoursMax: 350, genre: 'Action RPG' },
};

// ── Review text templates by platform & product ──

const AMAZON_TEMPLATES = {
  prod_001: [ // Headphones
    { r: 5, t: "Verified Purchase. The 45dB hybrid ANC on the Voyage Horizon is phenomenal. Completely silences AC hum and busy street traffic. 40mm beryllium drivers give crystal clear highs and deep punchy bass. Battery lasted me 48 hours on a single charge." },
    { r: 5, t: "Superb build quality! Memory foam ear cushions are ultra-soft and don't press on my spectacles even after 6 hours of continuous editing. LDAC Hi-Res audio is noticeably cleaner than standard AAC." },
    { r: 4, t: "Great soundstage and ANC. Multipoint connection between my MacBook and iPhone works seamlessly. Only minor complaint is the carrying case is slightly bulky, but it protects the headphones well." },
    { r: 5, t: "Amazon delivery was lightning fast. Noise cancellation rivals flagship brands at half the price. Fast charging gave me 6 hours of playback in just 10 minutes of plugging in." },
    { r: 4, t: "Balanced sound signature right out of the box. Mids and vocals are clear, ideal for acoustic tracks and podcasts. ANC transparency mode sounds natural with minimal white noise." },
    { r: 3, t: "Sound quality is very good, but the headband feels a little tight for large head sizes initially. It loosened up after a week. Battery life easily delivers 40+ hours." },
    { r: 5, t: "Outstanding value for money. The mic call quality with AI beamforming worked great on outdoor Zoom calls. Amazon Prime 1-day delivery with secure packaging." },
    { r: 2, t: "ANC is effective, but Bluetooth occasionally had a brief stutter when walking past microwave ovens. Re-pairing helped, but Voyage should release a firmware patch." },
    { r: 5, t: "Best wireless headphones under 10k! The beryllium drivers make every instrument distinct. Premium matte finish feels luxurious." },
    { r: 4, t: "Solid build and comfortable earcups. The physical buttons are intuitive and much better than annoying touch gestures. 45dB ANC blocks flight cabin drone easily." },
    { r: 5, t: "Extremely satisfied with this purchase. Zero ear fatigue during long flights. Battery meter barely dropped after 3 days of regular use." },
    { r: 1, t: "Received a box with a crushed corner from courier handling, though the headphones inside were undamaged. Customer service resolved the exchange quickly." },
    { r: 4, t: "Excellent audio resolution. Bass is tight without bleeding into the mid frequencies. Bluetooth 5.4 connectivity has great range across rooms." },
    { r: 5, t: "Packaging was pristine with double boxing. Comes with high-grade braided 3.5mm aux cable and USB-C cable. 5 stars for Voyage audio engineering!" },
    { r: 3, t: "Decent headphones. ANC is good in office environments, but wind noise can be audible when cycling. Sound profile is warm and pleasant." },
    { r: 5, t: "The Horizon ANC exceeded all expectations. Vocal clarity in podcasts and cinematic bass in action movies are top tier. Worth every rupee." },
    { r: 4, t: "Very comfortable over-ear design. Fast delivery by Amazon India. Microphone picks up speech clearly without catching background keyboard clatter." },
    { r: 5, t: "Hi-Res LDAC support on Android works flawlessly. The dynamic range on classical and jazz tracks is breathtaking." },
    { r: 2, t: "Good sound but earpads get a little warm in non-AC rooms during peak summer. Otherwise ANC and battery are stellar." },
    { r: 5, t: "Battery longevity is ridiculous — charged it on Monday and still had 40% battery by Sunday night with ANC enabled! Highly recommended." },
    { r: 4, t: "Sleek aesthetic with zero gaudy branding. Sound isolation is great even without ANC switched on due to plush memory foam seal." },
    { r: 5, t: "Upgraded from budget earbuds and the difference in audio detail is night and day. Voyage Horizon ANC is the real deal." },
    { r: 3, t: "Satisfactory overall. Button clicks feel a bit clicky, but Bluetooth latency is low enough to watch movies without lipsync delay." },
    { r: 5, t: "Unbeatable price-to-performance ratio. Clean bass, open mids, and crisp highs. Amazon delivered in under 24 hours in Bangalore." },
    { r: 4, t: "Durable metal headband adjustment mechanism. Tested in office and flights, ANC blocks background chatter effectively." },
  ],
  prod_002: [ // Mic
    { r: 5, t: "Verified Purchase. The Voyage StreamCast Pro has pristine studio clarity! 192kHz/24-bit recording makes voiceovers sound radio-grade with zero background hiss." },
    { r: 5, t: "Heavy weighted die-cast metal stand keeps it rock solid on the desk. Zero-latency 3.5mm headphone jack is essential for real-time monitoring." },
    { r: 4, t: "Cardioid pickup pattern does an amazing job rejecting mechanical keyboard noise from behind the mic. Gain dial is silky smooth." },
    { r: 5, t: "Amazon Prime delivery was flawless. Internal pop filter handles harsh plosives easily. Plug and play on Windows 11 with no driver headache." },
    { r: 4, t: "Omni mode worked wonderfully for our 3-person podcast table recording. Clean sound with warm vocal presence." },
    { r: 3, t: "Microphone audio quality is 5/5, but the included USB-C cable could be a bit longer for boom arm cable routing." },
    { r: 5, t: "Tap-to-mute sensor on top with LED indicator prevents accidental hot mic moments during live streams. Phenomenal build quality!" },
    { r: 2, t: "Picks up slight desk vibrations if not using a boom arm, but mounting it on a shockmount completely fixed the desk thuds." },
    { r: 5, t: "Exceptional clarity for voice acting and Discord calls. Friends noticed the audio upgrade immediately. Best condenser mic under 8k." },
    { r: 4, t: "Solid metal chassis with matte black powder coating. The cardioid pattern focuses sharply on vocals and cuts room echo." },
    { r: 5, t: "Delivered next day in pristine packaging. Clean gain staging with high headroom, no clipping even during loud commentary." },
    { r: 4, t: "Great value for money. Frequency response curve has a pleasant presence boost around 4kHz that makes voices cut through." },
    { r: 1, t: "Mute button LED had a slight cosmetic flicker on first unit, but Amazon replaced it within 2 days. Replacement is flawless." },
    { r: 5, t: "Plug-and-play simplicity on both PC and Mac. Tested with OBS and Audacity, noise floor is remarkably quiet." },
    { r: 3, t: "Good mic for work-from-home meetings. Sensitivity is high, so make sure to keep gain around 40-50% for optimal results." },
    { r: 5, t: "Studio-grade condenser capsule captures natural warmth and low-end proximity effect without muddiness." },
    { r: 4, t: "The dual polar pattern toggle is super handy. Amazon packaging was secure with ample foam padding." },
    { r: 5, t: "Vocals sound rich and broadcast-ready right out of the box. No EQ needed for standard YouTube commentary." },
    { r: 4, t: "Sturdy threaded base fits standard 5/8 inch boom arm adapters easily. High quality metal construction throughout." },
    { r: 5, t: "Crisp highs and warm low end. The internal shockmount dampens accidental desk bumps surprisingly well." },
    { r: 2, t: "Sensitive to ambient room echo in uncarpeted rooms, but acoustic foam behind the desk cured the reflections." },
    { r: 5, t: "Far superior to headset mics. Clean audio with impressive dynamic range. Excellent customer support from Voyage." },
    { r: 4, t: "Very easy to dial in the sweet spot with the front gain knob. LED status light is subtle and not distracting on camera." },
    { r: 5, t: "Outstanding microphone for streaming and podcasting. High resolution audio reproduction and rugged construction." },
    { r: 3, t: "Decent mic for the price. Works reliably for corporate conference calls and Discord gaming squads." },
  ],
  prod_003: [ // Mouse
    { r: 5, t: "Verified Purchase. The Voyage Apex Wireless at 58 grams feels like moving air! PixArt 26,000 DPI sensor tracking is 1:1 pixel accurate with zero jitter." },
    { r: 5, t: "Optical switches feel snappy and crisp with instant reset. No chance of double-clicking issues. PTFE glides glide smoothly across my cloth pad." },
    { r: 4, t: "Battery life is astounding — over 80 hours on 1000Hz polling rate. 2.4GHz wireless dongle connection is rock solid without dropouts." },
    { r: 5, t: "Amazon delivery in 24 hours. The ergonomic symmetrical shape fits medium and large hands perfectly for claw and fingertip grip." },
    { r: 4, t: "Lightweight shell without honeycomb holes keeps dust and moisture out. Build quality feels rigid with zero creaking when squeezed." },
    { r: 3, t: "Scroll wheel steps are very tactile and defined, which is great for weapon switching, though middle click requires slightly firm pressure." },
    { r: 5, t: "Flicking and tracking in Valorant and Apex Legends feels effortless. Weight distribution is perfectly centered." },
    { r: 2, t: "Mouse feet are great, but the included paracord charging cable is slightly stiff. Once charged though, the wireless freedom is unmatched." },
    { r: 5, t: "Zero sensor delay over 2.4GHz wireless. The lightweight build completely eliminated my wrist fatigue during marathon gaming sessions." },
    { r: 4, t: "Super clean aesthetic with no tacky gamer RGB logos. Web-based configuration tool means no bloated software running in background." },
    { r: 5, t: "Pristine packaging from Amazon. The matte coating provides great grip even when palms get sweaty during clutch rounds." },
    { r: 4, t: "Very satisfying optical switch actuation. Battery charges to full in less than an hour via USB Type-C." },
    { r: 1, t: "USB wireless dongle was missing from the accessory box, but Amazon immediate replacement sent a complete set the next day." },
    { r: 5, t: "Top tier wireless esports mouse. Tracks flawlessly on both Cordura and cloth mousepads. Exceptional value under 4k." },
    { r: 3, t: "Good wireless mouse for competitive gaming. Side buttons are placed well, though right click is slightly louder than left click." },
    { r: 5, t: "The 58g weight combined with 100% virgin PTFE skates makes micro-adjustments in tactical shooters so precise." },
    { r: 4, t: "Reliable sleep wake-up time is instantaneous. Amazon shipping was fast and secure." },
    { r: 5, t: "Replaced my heavy 100g mouse and my aim consistency improved dramatically. Sensor tracking never spins out even on rapid swipes." },
    { r: 4, t: "DPI switch on the underside prevents accidental DPI changes mid-fight. Very well thought out gaming peripheral." },
    { r: 5, t: "Phenomenal battery longevity. Two weeks of heavy daily use and still sitting comfortably above 40% battery." },
    { r: 2, t: "Shape is great for claw grip, but pure palm grippers with very large hands might prefer a slightly taller palm hump." },
    { r: 5, t: "Optical switch durability rated for 90 million clicks. Crisp tactile feedback and featherlight glide." },
    { r: 4, t: "High polling rate stability with zero frame drops. Voyage Apex is easily one of the best wireless mice in this segment." },
    { r: 5, t: "Flawless wireless performance, long-lasting battery, and ultra-lightweight ergonomic chassis. 5 stars all the way!" },
    { r: 3, t: "Solid gaming mouse. Lightweight build and responsive sensor. Works smoothly on Windows 11." },
  ],
  prod_004: [ // Monitor
    { r: 5, t: "Verified Purchase. The Voyage UltraVision 27\" Fast IPS panel is gorgeous! 165Hz at 2560x1440 QHD offers incredible sharpness and buttery smooth motion." },
    { r: 5, t: "1ms response time with AMD FreeSync Premium eliminates tearing and motion ghosting completely. Color accuracy out of the box with 99% sRGB is spot on." },
    { r: 4, t: "The USB-C 65W Power Delivery is a lifesaver — connects my laptop for video, data, and charging with a single clean cable. Desk looks super neat." },
    { r: 5, t: "Amazon delivery handled this large monitor with utmost care. Heavy-duty thermocol packaging, zero dead pixels, and minimal IPS glow." },
    { r: 4, t: "Ergonomic stand supports height adjustment, tilt, swivel, and full 90-degree pivot for portrait coding. Sturdy metal base." },
    { r: 3, t: "HDR400 is decent for brightness highlights in games, but don't expect OLED-level deep blacks. SDR colors and 165Hz speed are fantastic though." },
    { r: 5, t: "Gaming on 1440p 165Hz is an absolute revelation coming from 1080p 60Hz. Text clarity for coding and reading documents is razor sharp." },
    { r: 2, t: "Built-in speakers are basic for notifications, but you'll definitely want external speakers or headphones for gaming and music." },
    { r: 5, t: "Zero backlight bleed on my panel! Verified with dark room tests. Great viewing angles and vibrant colors for graphic design work." },
    { r: 4, t: "OSD joystick navigation behind the bezel is intuitive. Pre-calibrated sRGB mode is accurate for photo and video editing." },
    { r: 5, t: "Delivered next morning by Amazon Prime in Bangalore. DisplayPort 1.4 and HDMI 2.0 cables both included in the box." },
    { r: 4, t: "Extremely thin bezels on three sides look modern and sleek in a dual-monitor setup. Stand has integrated cable routing hole." },
    { r: 1, t: "Delivery was delayed by one day due to heavy rains, but the monitor arrived well protected in double packaging." },
    { r: 5, t: "Buttery smooth 165Hz gameplay in Cyberpunk and Warzone. FreeSync keeps frame rates completely synchronized with my RTX GPU." },
    { r: 3, t: "Good gaming monitor. Stand takes up some desk depth, so consider a VESA monitor arm if you have a shallow desk." },
    { r: 5, t: "VESA 100x100 mount compatible. 350 nits typical brightness is plenty bright even in sunlit home office rooms." },
    { r: 4, t: "Fast IPS technology provides vibrant colors without the dark-level smearing typical of VA panels. Very happy with this display." },
    { r: 5, t: "Text rendering is clean with zero fringing. 27 inches is the absolute sweet spot for 1440p pixel density." },
    { r: 4, t: "Anti-glare 3H coating diffuses window reflections effectively without degrading image sharpness. Solid build quality." },
    { r: 5, t: "Excellent value for money. 165Hz, QHD IPS, USB-C 65W PD, and height adjustable stand at under 20k is unbeatable." },
    { r: 2, t: "Power brick is slightly large, but it powers the monitor and supplies 65W to my laptop simultaneously." },
    { r: 5, t: "Tested for ghosting with UFO test — motion clarity at 165Hz with overdrive set to fast is pristine with zero inverse ghosting." },
    { r: 4, t: "Great customer support from Voyage answering my query on dual monitor daisy chaining. Amazon packaging was secure." },
    { r: 5, t: "High refresh rate, sharp resolution, rich color gamut, and ergonomic stand. Voyage UltraVision 27 is a triumph!" },
    { r: 3, t: "Decent monitor for productivity and casual gaming. Good viewing angles and responsive IPS panel." },
  ]
};

const FLIPKART_TEMPLATES = {
  prod_001: [ // Headphones
    { r: 5, t: "Flipkart Big Billion Days deal! Voyage Horizon ANC headphones sound absolutely mind-blowing. Heavy bass, clear vocals, and ANC blocks Delhi metro noise completely. Paisa vasool!" },
    { r: 5, t: "Super fast Flipkart delivery, received in 2 days in Pune! Ear cushions are so soft, memory foam feels premium. Battery backup easily lasts 45+ hours." },
    { r: 4, t: "Sound quality bahut acchi hai. Bass punchy hai without distortion. Bluetooth connection instantly pairs with my phone and laptop." },
    { r: 5, t: "Flipkart Assured quality. The 45dB ANC creates pin-drop silence in noisy rooms. Type-C fast charging is super convenient." },
    { r: 4, t: "Build quality solid hai, metal headband feels durable. Soundstage is wide for gaming footsteps and watching movies." },
    { r: 3, t: "Good product for the price. Sound is clear and balanced. ANC is effective, but earcups feel slightly warm after 3 hours." },
    { r: 5, t: "Best wireless headphones under 6k on Flipkart! Beautiful matte finish and comes with premium protective travel pouch." },
    { r: 2, t: "Delivery box had slight crease, but headphones inside were safe in bubble wrap. Mic is good for calls." },
    { r: 5, t: "Lajawab sound quality! Beryllium drivers deliver crisp highs and thumping bass. Very happy with Voyage brand." },
    { r: 4, t: "Comfortable fit for long study and work sessions. Noise cancellation cuts fan and traffic noise smoothly." },
    { r: 5, t: "Flipkart SuperCoins discount made this an unbeatable deal. 50 hours battery life is genuine!" },
    { r: 4, t: "Mic picks up voice clearly on WhatsApp and Zoom calls. Physical buttons are easy to locate by touch." },
    { r: 1, t: "Courier guy delivered in evening instead of morning slot. Product is working fine though." },
    { r: 5, t: "Awesome ANC performance! Tested on local train commute in Mumbai, background noise was 90% silenced." },
    { r: 3, t: "Decent headphones. Bass is strong, battery backup is good for 4-5 days of normal usage." },
    { r: 5, t: "High resolution audio quality with LDAC. Premium memory foam doesn't hurt ears even with glasses." },
    { r: 4, t: "Value for money product on Flipkart. Sound separation between instruments is crisp." },
    { r: 5, t: "Battery life ekdum zabardast! Charged once on weekend and still going strong after whole week." },
    { r: 4, t: "Fast Bluetooth 5.4 pairing. Range is great, works across two rooms without cutting out." },
    { r: 2, t: "Sound quality 5 star hai but white color gets dirty easily. Black color variant is safer." },
    { r: 5, t: "Exceeded my expectations. Packaging was neat and clean, product looks very premium." },
    { r: 4, t: "Crisp treble and deep bass. ANC transparency mode is useful when someone speaks to you." },
    { r: 5, t: "Super happy with Voyage Horizon ANC! Best purchase on Flipkart electronics." },
    { r: 3, t: "Good everyday headphones for office work and music. Decent noise cancellation." },
    { r: 5, t: "Solid build, amazing sound, top tier battery backup. 5 stars for Voyage!" },
  ],
  prod_002: [ // Mic
    { r: 5, t: "Flipkart delivery was super fast! Voyage StreamCast Pro mic is a game changer for my YouTube gaming channel. Audio is crisp and clean." },
    { r: 5, t: "Heavy metal stand, doesn't tip over. 192kHz/24-bit recording captures deep radio-like voice clarity. Paisa vasool deal on Flipkart!" },
    { r: 4, t: "Cardioid pickup pattern cuts background room noise effectively. Mute button with LED indicator on top is very convenient." },
    { r: 5, t: "Flipkart Assured seller. Built-in pop filter handles plosives smoothly. Zero latency headphone monitoring works like a charm." },
    { r: 4, t: "Voice recording quality is studio grade. Front gain control knob has smooth resistance and no crackling." },
    { r: 3, t: "Mic build is solid heavy metal. Sound quality is very clear, but make sure to use it around 6 inches from mouth for best results." },
    { r: 5, t: "My Discord friends asked if I bought a 15k professional broadcast mic! Voyage StreamCast Pro delivers unbelievable value." },
    { r: 2, t: "Included USB cable is 1.8 meters, which is fine for laptop but slightly short for my under-desk PC cabinet." },
    { r: 5, t: "Plug and play on Windows 10 without needing any complex drivers. Clean sound with warm vocal presence." },
    { r: 4, t: "Great condenser mic for teaching online classes and recording podcasts. Background noise is well suppressed." },
    { r: 5, t: "Excellent packaging by Flipkart, delivered safely with bubble wrap. Matte black finish looks professional on camera." },
    { r: 4, t: "Omnidirectional mode is great when two people are speaking across the desk. Both voices come through balanced." },
    { r: 1, t: "First package had broken outer tape, but replacement was arranged promptly. Mic works flawlessly." },
    { r: 5, t: "Audio clarity is 10 times better than standard headset mic. No hiss or buzzing noise in recordings." },
    { r: 3, t: "Decent USB mic for streaming. Works well with OBS and Audacity. Sturdy desk stand." },
    { r: 5, t: "Smooth gain dial and zero-latency monitoring make recording voiceovers so effortless. Top recommendation!" },
    { r: 4, t: "Good value for money on Flipkart. Metal chassis feels durable and built to last." },
    { r: 5, t: "Pristine vocal fidelity! High frequencies are crisp without being sibilant or harsh." },
    { r: 4, t: "Tap to mute sensor is completely silent, no mechanical click sound recorded into the audio track." },
    { r: 2, t: "Sensors are sensitive, so keep it away from loud computer fans for best vocal isolation." },
    { r: 5, t: "Amazing sound recording quality. Ideal for YouTube, podcasting, and corporate meetings." },
    { r: 4, t: "Sturdy threads on bottom fit my boom arm stand perfectly. Very happy with Flipkart purchase." },
    { r: 5, t: "High quality condenser capsule captures rich low-end and vocal warmth. Worth every single rupee!" },
    { r: 3, t: "Good mic for streaming on budget. Solid build quality and clear audio pickup." },
    { r: 5, t: "Broadcast-grade audio on a budget. Voyage brand has done an outstanding job with StreamCast Pro." },
  ],
  prod_003: [ // Mouse
    { r: 5, t: "Flipkart Big Billion Days grab! Voyage Apex Wireless at 58 grams feels featherlight in hand. Aiming in Valorant and CS2 is so buttery smooth!" },
    { r: 5, t: "Super fast Flipkart delivery to Hyderabad in 2 days. Optical switches have zero debounce delay and pure PTFE feet glide effortlessly." },
    { r: 4, t: "Sensor tracking on 26k DPI PixArt is flawless. Battery backup easily lasts 2 to 3 weeks of daily gaming." },
    { r: 5, t: "Flipkart Assured product. The matte texture gives excellent grip even during intense ranked matches. No creaking in shell." },
    { r: 4, t: "Ergonomic shape is comfortable for both claw and fingertip grip. USB-C charging port is fast and convenient." },
    { r: 3, t: "Mouse is extremely light and responsive. Scroll wheel clicks are tactile, though scroll steps are a bit stiff initially." },
    { r: 5, t: "Zero wireless delay with the 2.4GHz USB receiver. Flick shots feel natural and micro-adjustments are pin-point accurate." },
    { r: 2, t: "Packaging box had slight corner bump during courier transit, but the mouse inside was safe in molded plastic." },
    { r: 5, t: "Best ultralight gaming mouse under 4000 on Flipkart! Battery lasts forever and tracking is top notch." },
    { r: 4, t: "Lightweight solid shell without holes keeps dirt away. Optical switch clicks feel crisp and responsive." },
    { r: 5, t: "My K/D ratio in competitive FPS improved noticeably. The 58g weight reduces wrist strain significantly." },
    { r: 4, t: "Great value for money. Polling rate is consistent at 1000Hz with zero jitter or spin-out issues." },
    { r: 1, t: "Delivery agent arrived late evening, but product was sealed and original Voyage inventory." },
    { r: 5, t: "Symmetrical design fits my hand perfectly. Fast wake-up from sleep mode with no stutter on first swipe." },
    { r: 3, t: "Good gaming mouse for the price. Battery backup is solid, optical switches feel snappy." },
    { r: 5, t: "PTFE skates glide like ice on my cloth mousepad. Clean look with no gaudy RGB distractions." },
    { r: 4, t: "DPI button on underside is smart so you don't accidentally switch DPI in the middle of a gunfight." },
    { r: 5, t: "Charged it once when it arrived 10 days ago and still on 60% battery. Wireless efficiency is phenomenal." },
    { r: 4, t: "Solid build quality, no creaking even when gripping hard during clutch rounds. Smooth Flipkart purchase." },
    { r: 2, t: "Very lightweight so takes a couple of days to get used to if switching from heavy 100g office mouse." },
    { r: 5, t: "Precision tracking, zero latency, light weight, and long battery life. 5 stars for Voyage Apex!" },
    { r: 4, t: "Optical switches mean no double clicking issue down the line. Super happy with this investment." },
    { r: 5, t: "Featherlight 58g wireless perfection. Glides effortlessly, clicks are instant, battery is endless." },
    { r: 3, t: "Decent wireless mouse for casual and competitive gaming. Comfortable grip." },
    { r: 5, t: "Top tier esports grade mouse on Flipkart. Voyage Apex Wireless is an absolute winner!" },
  ],
  prod_004: [ // Monitor
    { r: 5, t: "Flipkart delivery was prompt with open box inspection! Voyage UltraVision 27\" QHD Fast IPS panel is stunning. 165Hz gaming at 1440p is butter smooth." },
    { r: 5, t: "Colors are super vibrant with 99% sRGB coverage. FreeSync Premium keeps frames totally fluid without screen tearing in AAA titles." },
    { r: 4, t: "The 65W Type-C port charges my office laptop while sending video signal through one cable. Minimalist desk setup accomplished!" },
    { r: 5, t: "Flipkart Assured gaming monitor. Heavy ergonomic stand allows smooth height adjustment and portrait rotation for programming." },
    { r: 4, t: "1440p resolution at 27 inches is the perfect pixel density — razor sharp fonts and crisp textures in games." },
    { r: 3, t: "Screen brightness is very good at 350 nits. HDR400 is decent, though the real highlight is the 165Hz Fast IPS panel speed." },
    { r: 5, t: "Zero dead pixels on arrival! Tested with full screen color slides. Beautiful slim bezels on three sides." },
    { r: 2, t: "Monitor package is quite large, but the thick styrofoam casing protected the screen completely during shipping." },
    { r: 5, t: "Upgraded from a 60Hz 1080p display and the jump to 165Hz 1440p is astonishing. Valorant and Forza Horizon look breathtaking." },
    { r: 4, t: "Fast response time with zero noticeable ghosting or inverse overshoot. Clean OSD menu with crosshair overlay." },
    { r: 5, t: "Got a great bank discount on Flipkart. Heavy metal base keeps monitor planted firmly with zero wobble." },
    { r: 4, t: "DisplayPort and HDMI ports are easy to access. Cable management clip on the stand keeps cords tidy." },
    { r: 1, t: "Delivery van had to wait 20 minutes for OTP verification, but packaging was intact and undamaged." },
    { r: 5, t: "IPS viewing angles are wide with zero color shifting from the sides. Ideal for both gaming and video editing work." },
    { r: 3, t: "Good gaming monitor for the price. Stand requires some desk space, but VESA 100x100 mounting is supported." },
    { r: 5, t: "Fast IPS motion clarity is fantastic. 1ms MPRT keeps fast panning camera movement clean and sharp." },
    { r: 4, t: "Solid build quality and modern aesthetics. USB-C 65W charging works seamlessly with my MacBook Air." },
    { r: 5, t: "Crisp 2K resolution makes multi-window multitasking so productive. 165Hz smoothness is addictive." },
    { r: 4, t: "Anti-glare screen coating cuts room window reflections effectively without grainy matte artifacts." },
    { r: 2, t: "Internal speakers are basic, but display quality and gaming performance are top tier." },
    { r: 5, t: "Exceptional gaming monitor on Flipkart. Vivid colors, fast 165Hz refresh rate, and sturdy adjustable stand." },
    { r: 4, t: "Great value for money in the 1440p high-refresh gaming display segment. No backlight bleeding on my unit." },
    { r: 5, t: "Buttery smooth 165Hz, crisp QHD resolution, and single cable USB-C dock. 5 stars for Voyage UltraVision!" },
    { r: 3, t: "Decent monitor for home office and gaming. Good colors and sharp display." },
    { r: 5, t: "Best 27 inch gaming monitor under 20k on Flipkart. Highly recommended to all PC gamers!" },
  ]
};

const JIOMART_TEMPLATES = {
  prod_001: [ // Headphones
    { r: 5, t: "JioMart express delivery arrived within 24 hours in Mumbai! Voyage Horizon ANC headphones are super comfortable for long work from home meetings." },
    { r: 5, t: "Sound quality is very rich and balanced. 45dB hybrid ANC blocks out street construction noise completely. Battery lasts all week!" },
    { r: 4, t: "Plush memory foam earcups don't cause any ear pain even after 8 hours of work calls. Great JioMart price deal." },
    { r: 5, t: "Quick delivery from local hub. Fast charging with USB-C gives hours of playback in minutes. Bluetooth connectivity is rock solid." },
    { r: 4, t: "Microphone captures clear voice without room echo during Microsoft Teams meetings. Soundstage for music is wide and pleasant." },
    { r: 3, t: "Good headphones for daily office commute. ANC works well, battery life is genuine 45-50 hours." },
    { r: 5, t: "Saved 40% on JioMart electronics sale. Premium packaging and excellent build quality on the metal slider." },
    { r: 2, t: "Delivery boy delivered late in the evening, but product was sealed in original Voyage box with warranty card." },
    { r: 5, t: "The 40mm beryllium drivers produce punchy bass and crystal clear instrument separation. Very satisfied!" },
    { r: 4, t: "Dual pairing between laptop and mobile works smoothly. ANC transparency mode is natural." },
    { r: 5, t: "Comfortable over-ear design. Doesn't clamp too tight on the head. Best ANC headphones in this budget." },
    { r: 4, t: "Durable matte black finish. Physical buttons are much easier to operate than temperamental touch sensors." },
    { r: 1, t: "Box had slight outer tape tear, but headphones and accessories inside were 100% brand new." },
    { r: 5, t: "Outstanding battery longevity. I only charge it twice a month with regular daily listening." },
    { r: 3, t: "Decent sound and good noise cancellation. Works reliably with Windows and Android." },
    { r: 5, t: "Clear audio on calls and great music fidelity. JioMart delivery was smooth and well tracked." },
    { r: 4, t: "Comes with braided 3.5mm aux cable and USB Type-C charging wire. Good value for money." },
    { r: 5, t: "High resolution LDAC support delivers studio grade audio. Very happy with Voyage brand quality." },
    { r: 4, t: "Noise cancellation helps me concentrate in busy open-plan office. Ear cushions seal well." },
    { r: 2, t: "A bit bulky around neck when resting, but on ears the weight distribution is very comfortable." },
    { r: 5, t: "Premium audio experience without paying luxury brand prices. 5 stars on JioMart!" },
    { r: 4, t: "Great sound isolation even when ANC is turned off. Solid construction." },
    { r: 5, t: "Clear highs, warm mids, and deep bass. Battery backup is unbelievable." },
    { r: 3, t: "Satisfactory performance for daily music listening and video meetings." },
    { r: 5, t: "Excellent ANC headphones from Voyage. Highly recommended for work and travel." },
  ],
  prod_002: [ // Mic
    { r: 5, t: "Ordered via JioMart for home office Zoom meetings and podcast recordings. Voyage StreamCast Pro provides crystal clear studio voice!" },
    { r: 5, t: "Heavy metal stand keeps it firmly in place on desk. 192kHz/24-bit audio resolution makes voice sound warm and professional." },
    { r: 4, t: "Cardioid pickup pattern eliminates fan noise and keyboard clicks from behind. Tap-to-mute button on top is super useful." },
    { r: 5, t: "Delivered next morning by JioMart express courier. Zero-latency headphone monitoring lets you hear your exact voice levels." },
    { r: 4, t: "Front gain control knob is smooth and tactile. Plug and play on Windows 11 with no complicated software setup." },
    { r: 3, t: "Very sensitive condenser capsule, so keep gain around 40% for natural speech without picking up distant background noise." },
    { r: 5, t: "Colleagues noticed the immediate upgrade in audio clarity on conference calls. Solid metal construction throughout." },
    { r: 2, t: "Desk stand is heavy which is good, but takes some space on compact desks. Boom arm mount works better for tight spaces." },
    { r: 5, t: "Internal pop filter softens harsh P and B plosive sounds. Vocal recordings come out clean and broadcast ready." },
    { r: 4, t: "Great value deal on JioMart. LED mute indicator prevents accidental unmuted conversations." },
    { r: 5, t: "Voice acting and voiceover recordings sound radio-grade with zero background hiss or electrical buzz." },
    { r: 4, t: "Omni mode allows recording interviews with two people sitting across each other with balanced pickup." },
    { r: 1, t: "Courier delivered during lunch break without calling first, but the product itself is 5/5 quality." },
    { r: 5, t: "Outstanding vocal warmth and high frequency clarity. Highly recommended for teachers and content creators." },
    { r: 3, t: "Decent USB condenser microphone for calls and casual streaming. Works reliably." },
    { r: 5, t: "Sturdy metal chassis with sleek matte finish. Professional audio equipment at a consumer price point." },
    { r: 4, t: "Good packaging with thick protective foam. Connected instantly to Mac and PC without drivers." },
    { r: 5, t: "Clear speech intelligibility without room boominess. Best mic purchase on JioMart electronics." },
    { r: 4, t: "High quality 24-bit audio conversion. Smooth gain staging and zero latency monitoring." },
    { r: 2, t: "Picks up heavy keyboard slamming if placed right next to keyboard, using a boom arm solved it." },
    { r: 5, t: "Fantastic microphone for podcasts, online tutorials, and work from home. 5 stars!" },
    { r: 4, t: "Solid build, clear sound, and practical tap-to-mute button. Very happy with Voyage brand." },
    { r: 5, t: "Studio sound quality at home. Broadcast ready voice recording with zero effort." },
    { r: 3, t: "Good microphone for office video calls and online meetings. Easy setup." },
    { r: 5, t: "Top tier USB studio microphone. Voyage StreamCast Pro exceeded all my expectations!" },
  ],
  prod_003: [ // Mouse
    { r: 5, t: "JioMart delivered the Voyage Apex Wireless mouse in 24 hours! Ultralight 58g weight makes office work and evening gaming effortless." },
    { r: 5, t: "PixArt 26,000 DPI sensor tracking is silky smooth on 1000Hz polling rate. Optical switches ensure zero double-clicking." },
    { r: 4, t: "Battery lasts for weeks on a single USB-C charge. 2.4GHz wireless dongle connection has zero input lag." },
    { r: 5, t: "Great JioMart discount price. Ergonomic shape fits comfortably in hand without causing wrist fatigue." },
    { r: 4, t: "Pure PTFE glides slide effortlessly across standard desk pads. Solid lightweight shell keeps dust out." },
    { r: 3, t: "Mouse is very lightweight and responsive. Scroll wheel clicks are firm and tactile." },
    { r: 5, t: "Replaced my heavy wireless mouse and moving the cursor feels effortless. Fast wake up from sleep mode." },
    { r: 2, t: "Takes a day to adjust to 58 grams if you are used to bulky 100g office mice, but once adjusted it is fantastic." },
    { r: 5, t: "Matte surface finish gives confident grip even during long work hours. Clean understated aesthetic." },
    { r: 4, t: "Optical switch clicks have very satisfying feedback. No software bloat required for standard DPI settings." },
    { r: 5, t: "Delivered safely in sealed original Voyage packaging. Wireless battery efficiency is phenomenal." },
    { r: 4, t: "Reliable 2.4GHz wireless range across the room. Symmetrical ergonomics fit medium hands well." },
    { r: 1, t: "Delivery boy took wrong turn in society, but product was in perfect condition." },
    { r: 5, t: "Best lightweight wireless mouse available on JioMart. Fast sensor and endless battery life." },
    { r: 3, t: "Good wireless mouse for home and office. Lightweight and responsive cursor control." },
    { r: 5, t: "Featherlight glide and zero sensor lag. Perfect for both productivity spreadsheets and casual gaming." },
    { r: 4, t: "USB-C fast charging cable is flexible and soft. Battery percentage stays high for weeks." },
    { r: 5, t: "Optical switch durability rated for 90M clicks gives peace of mind. Excellent engineering by Voyage." },
    { r: 4, t: "Crisp side button placement makes browsing forward and back intuitive and quick." },
    { r: 2, t: "Included cable is USB-A to USB-C, so needed a small adapter for my MacBook Thunderbolt port." },
    { r: 5, t: "Lightweight, wireless, accurate, and durable. 5 stars for Voyage Apex!" },
    { r: 4, t: "Solid build quality with no creaks or flex in the body. Great value on JioMart." },
    { r: 5, t: "Smooth tracking across all surfaces. High polling rate makes cursor motion buttery." },
    { r: 3, t: "Decent wireless mouse for everyday computing and gaming. Comfortable in palm." },
    { r: 5, t: "Exceptional wireless mouse. Voyage Apex delivers premium ergonomics and top-tier sensor accuracy." },
  ],
  prod_004: [ // Monitor
    { r: 5, t: "JioMart electronics delivery handled the Voyage UltraVision 27\" monitor with great care! 2560x1440 QHD IPS panel is super sharp." },
    { r: 5, t: "165Hz refresh rate makes moving windows and gaming amazingly smooth. AMD FreeSync Premium prevents screen tearing." },
    { r: 4, t: "The 65W USB-C Power Delivery powers my office laptop while transmitting video and data over a single wire. Clean desk setup!" },
    { r: 5, t: "Zero dead pixels on my screen. 99% sRGB color gamut produces vibrant natural colors for photo and document review." },
    { r: 4, t: "Sturdy ergonomic stand with full height adjustment, tilt, swivel, and 90-degree pivot for vertical document reading." },
    { r: 3, t: "Screen is plenty bright at 350 nits. HDR400 provides good contrast highlights in supported video content." },
    { r: 5, t: "Massive upgrade for my home office setup. 27 inches is the ideal size for 1440p dual-window productivity." },
    { r: 2, t: "Monitor box is substantial in size, but internal styrofoam protected the screen completely during transit." },
    { r: 5, t: "Crisp text rendering with zero pixelation. High refresh rate eliminates cursor blur when scrolling through spreadsheets." },
    { r: 4, t: "Anti-glare 3H matte coating cuts down reflection from room lights. Wide IPS viewing angles." },
    { r: 5, t: "Great JioMart deal on a high-refresh QHD monitor. Heavy metal base prevents any screen shake." },
    { r: 4, t: "Includes both DisplayPort and HDMI cables in the box. OSD joystick makes adjusting brightness effortless." },
    { r: 1, t: "Delivery arrived on Sunday afternoon instead of Saturday morning, but product is brand new and pristine." },
    { r: 5, t: "Fast IPS panel has 1ms response time with zero dark-level smearing. Great for both work and gaming." },
    { r: 3, t: "Good 1440p monitor. Built-in speakers are basic, but display quality is top notch." },
    { r: 5, t: "Single cable USB-C docking functionality transforms laptop workflow. Clean setup with zero clutter." },
    { r: 4, t: "Slim three-sided borderless bezels look sleek and modern. Stand cable pass-through works well." },
    { r: 5, t: "Color accuracy is factory calibrated and looks natural right out of the box with no manual tweaking needed." },
    { r: 4, t: "Sturdy VESA 100x100 mounting holes on back allowed easy mounting to my monitor arm." },
    { r: 2, t: "Power brick is slightly chunky, but it supplies 65W charging to laptop so you don't need a separate laptop charger." },
    { r: 5, t: "Outstanding QHD 165Hz monitor from Voyage. Sharp visuals, smooth refresh rate, and versatile connectivity." },
    { r: 4, t: "High refresh rate is gentle on the eyes during 10-hour workdays. Highly recommended!" },
    { r: 5, t: "Vivid IPS colors, crisp 1440p resolution, and 165Hz fluid motion. 5 stars on JioMart!" },
    { r: 3, t: "Decent monitor for home office and entertainment. Good viewing angles." },
    { r: 5, t: "Best 27-inch gaming and productivity monitor in this price bracket. Voyage UltraVision is exceptional." },
  ]
};

const BRAND_TEMPLATES = {
  prod_001: [ // Headphones
    { r: 5, t: "Purchased directly from the Voyage official store (voyage.tech). Premium unboxing experience with branded magnetic closure box. The 45dB hybrid ANC is eerily quiet." },
    { r: 5, t: "Direct warranty registration was automatic upon order. 40mm beryllium drivers offer a studio-flat acoustic response with immense detail and zero distortion." },
    { r: 4, t: "LDAC Hi-Res audio decoding over Bluetooth 5.4 works flawlessly with my Sony DAP. Battery life surpassed 50 hours on testing with ANC active." },
    { r: 5, t: "Voyage customer support answered my technical query on EQ curves within 2 hours. Ultra-plush memory foam earpads seal comfortably around ears." },
    { r: 4, t: "Audiophile-grade tuning with punchy sub-bass that doesn't bleed into the midrange. Braided 3.5mm cable included for zero-latency studio mixing." },
    { r: 3, t: "Very solid construction with aircraft-grade aluminum hinges. Earpads are slightly warm after 4 hours, but soundstage is breathtaking." },
    { r: 5, t: "Direct store exclusive discount made this an exceptional value. AI beamforming mic performs great during noisy outdoor calls." },
    { r: 2, t: "Had a minor firmware update glitch on initial Bluetooth pairing, but Voyage web utility updated it to v1.2 seamlessly." },
    { r: 5, t: "The Horizon ANC rivals studio reference monitors in sonic fidelity. Vocals feel intimate and percussion hits have realistic attack." },
    { r: 4, t: "Fast shipping with express courier tracking. The hard-shell travel case has dedicated slots for all cables and flight adapter." },
    { r: 5, t: "Zero hiss noise floor on ANC. Transparency mode reproduces ambient sounds with accurate stereo localization." },
    { r: 4, t: "Physical tactile controls are responsive and prevent accidental pauses. Matte finish resists fingerprints effectively." },
    { r: 1, t: "Courier tracking link took 24 hours to become active on carrier site, but delivery arrived on schedule." },
    { r: 5, t: "Outstanding battery efficiency. One full charge powered a round-trip international flight with plenty of juice to spare." },
    { r: 3, t: "Clean neutral sound signature. Audiophiles will appreciate the lack of boomy artificial mid-bass boost." },
    { r: 5, t: "Voyage has established themselves as a serious contender in high-end personal audio. Horizon ANC is an engineering marvel." },
    { r: 4, t: "Multipoint connection switches between laptop audio and phone calls with zero delay. Very intuitive." },
    { r: 5, t: "Memory foam comfort is top tier. Clamping force is dialed in perfectly to prevent slipping without causing temple fatigue." },
    { r: 4, t: "High dynamic range and instrument separation. Orchestral soundtracks reveal micro-details previously unheard." },
    { r: 2, t: "Heavier than cheap plastic headphones due to metal reinforced structure, but durability is top notch." },
    { r: 5, t: "Exceptional audio engineering, premium materials, and responsive official brand support. 5 stars!" },
    { r: 4, t: "Fast USB-C charging protocol delivers 6 hours of playtime in just 10 minutes. Solid value." },
    { r: 5, t: "Studio clarity meets lifestyle ANC. Voyage Horizon ANC is the best headphone investment I've made." },
    { r: 3, t: "Decent high-resolution headphones with effective noise isolation and long battery life." },
    { r: 5, t: "A masterpiece of acoustic performance and comfort. Official brand store service was exemplary." },
  ],
  prod_002: [ // Mic
    { r: 5, t: "Ordered direct from the Voyage brand store. Voyage StreamCast Pro arrived in premium foam-padded packaging with gold-plated USB-C connector." },
    { r: 5, t: "192kHz/24-bit studio bitrate produces velvety vocal clarity. Cardioid mode rejects mechanical keyboard clicks from behind the microphone." },
    { r: 4, t: "Heavy cast-alloy base weighs over 700g, ensuring it never shifts during enthusiastic stream commentary. Zero-latency headphone monitoring." },
    { r: 5, t: "Tap-to-mute capacitive sensor on top with dual-color LED ring is completely silent when toggling. Professional broadcast finish." },
    { r: 4, t: "Built-in multilayer pop filter eliminates harsh plosives without requiring an awkward external mesh shield in front of camera." },
    { r: 3, t: "High sensitivity requires setting gain to around 40% in untreated bedrooms, but vocal warmth and proximity effect are rich." },
    { r: 5, t: "Voyage official store warranty gives 2 full years of coverage. Voice recordings sound ready for master mix right out of the box." },
    { r: 2, t: "Desk stand is sturdy, though attaching to a boom arm via the standard 5/8 inch brass thread isolates it even better." },
    { r: 5, t: "Clean gain stage with exceptionally low noise floor. No background static or electrical interference." },
    { r: 4, t: "Omni polar pattern mode is great for acoustic guitar recordings and multi-person podcast interviews." },
    { r: 5, t: "Fast express dispatch from Voyage warehouse. Seamless plug-and-play setup on Windows, macOS, and Linux." },
    { r: 4, t: "Front headphone volume dial and master gain knob both have smooth damped rotation with no wobbly play." },
    { r: 1, t: "Outer packaging box had a tiny dent on corner, but internal high-density foam kept the mic in showroom condition." },
    { r: 5, t: "Crystal clear frequency response with gentle presence lift around 4kHz that makes speech articulate and intelligible." },
    { r: 3, t: "Good condenser microphone for streamers and creators. Built like a tank with metal construction." },
    { r: 5, t: "Broadcast-grade vocal warmth without needing expensive XLR audio interfaces or preamps. USB-C simplicity." },
    { r: 4, t: "Official store customer support was very knowledgeable when answering polar pattern isolation questions." },
    { r: 5, t: "Superb voiceover clarity for video production. Background ambient hum is naturally suppressed by the cardioid capsule." },
    { r: 4, t: "Sturdy shockmount bracket integrated into the stand dampens desk vibrations effectively." },
    { r: 2, t: "Requires close mic technique for optimal radio broadcast tone, which is typical of all studio condenser capsules." },
    { r: 5, t: "Unbeatable value for prosumer audio creators. Voyage StreamCast Pro sets a new benchmark in USB microphones." },
    { r: 4, t: "High resolution 24-bit audio depth captures nuanced vocal inflection and dynamic range effortlessly." },
    { r: 5, t: "Flawless build quality, pristine sound fidelity, and premium official store unboxing experience." },
    { r: 3, t: "Decent studio microphone for podcasts and calls. Solid metal construction." },
    { r: 5, t: "Five stars across the board. The StreamCast Pro is an essential tool for any serious content creator." },
  ],
  prod_003: [ // Mouse
    { r: 5, t: "Direct brand store exclusive purchase. The Voyage Apex Wireless at 58 grams is an engineering feat! Optical switches have zero debounce latency." },
    { r: 5, t: "PixArt 26,000 DPI sensor tracking with 1000Hz polling rate offers 1:1 raw input with zero smoothing or acceleration. My aim feels instantaneous." },
    { r: 4, t: "Pure 100% virgin PTFE skates glide effortlessly across glass and cloth pads. Symmetrical ergonomic chassis provides solid palm support." },
    { r: 5, t: "Official store firmware update tool is entirely web-based — zero bloatware running in the background consuming CPU cycles!" },
    { r: 4, t: "Battery efficiency is astounding: 90 hours of continuous competitive gaming on a single charge. USB-C paracord cable is featherlight." },
    { r: 3, t: "Tactile scroll wheel steps are defined and sharp. Mouse clicks are on the firmer side of optical switches, which prevents misclicks." },
    { r: 5, t: "Solid structural integrity with zero shell flex or side creaking despite the ultra-low 58g weight. No honeycomb holes to collect sweat." },
    { r: 2, t: "Shape is geared toward claw and fingertip grip styles; extreme palm grippers with very large hands might prefer a higher rear hump." },
    { r: 5, t: "The 2.4GHz wireless dongle pairing has zero packet drops even in high-interference 2.4GHz office environments." },
    { r: 4, t: "DPI switch and power toggle on bottom prevent accidental adjustments during high-intensity tournament matches." },
    { r: 5, t: "Official Voyage packaging included spare PTFE replacement feet and textured grip tapes. Exceptional attention to detail." },
    { r: 4, t: "Matte coating feels velvety and dry, maintaining strong grip during sweaty clutch overtime rounds." },
    { r: 1, t: "Shipping courier had a 24-hour weather delay, but Voyage customer support proactively emailed tracking updates." },
    { r: 5, t: "Optical switch durability rated for 90 million clicks with zero chance of double click failure. A true competitive esports weapon." },
    { r: 3, t: "Very lightweight wireless gaming mouse. Sensor performance is flawless, side buttons are crisp." },
    { r: 5, t: "Flicking and tracking in tactical shooters feels like moving your own hand without physical resistance." },
    { r: 4, t: "Battery level LED indicator under the scroll wheel subtly warns when charge dips below 15%." },
    { r: 5, t: "Fast wake-up from sleep mode in under 1 millisecond. No cursor stutter on first movement." },
    { r: 4, t: "Solid build quality, premium optical switches, and balanced center of gravity. Worth every penny." },
    { r: 2, t: "Takes a few games to calibrate your muscle memory to such a lightweight mouse, but aim ceiling is much higher." },
    { r: 5, t: "The best lightweight wireless mouse on the market today. Voyage Apex is a masterpiece of esports engineering." },
    { r: 4, t: "Smooth PTFE glides, responsive optical clicks, and rock-solid 2.4GHz connectivity." },
    { r: 5, t: "Flawless tracking, 90-hour battery life, and 58g featherweight build. 5 stars for Voyage Apex!" },
    { r: 3, t: "Good wireless mouse with accurate sensor and durable optical switches." },
    { r: 5, t: "Elite competitive esports performance direct from Voyage official store. Couldn't ask for better." },
  ],
  prod_004: [ // Monitor
    { r: 5, t: "Direct purchase from Voyage brand store. Voyage UltraVision 27\" Fast IPS QHD monitor arrived via specialized fragile courier in perfect condition." },
    { r: 5, t: "2560x1440 resolution at 165Hz with 1ms MPRT response time delivers breathtaking motion clarity. Zero dark-level smearing or overshoot." },
    { r: 4, t: "The USB-C 65W Power Delivery port turns this monitor into a complete docking station for my workstation laptop. Single cable simplicity!" },
    { r: 5, t: "Factory color calibration report included in the box showed Delta E < 1.8 across all 99% sRGB color patches. Color grading is accurate." },
    { r: 4, t: "Heavy-duty ergonomic stand allows smooth height adjustment, swivel, tilt, and full 90-degree pivot for portrait coding and review." },
    { r: 3, t: "HDR400 delivers punchy highlight accents in supported video and games. SDR contrast and 350 nits brightness are excellent." },
    { r: 5, t: "Zero dead pixels, zero stuck subpixels, and virtually zero IPS glow. The panel uniformity is remarkably clean across the entire 27 inches." },
    { r: 2, t: "Power adapter brick is moderately sized, but it houses the internal power supply and 65W laptop charger together." },
    { r: 5, t: "Gaming at 1440p 165Hz with AMD FreeSync Premium is fluid and immersive. Text sharpness for programming is crystal clear." },
    { r: 4, t: "OSD joystick on rear bezel is fast and intuitive. Dedicated sRGB and DCI-P3 color profiles are easy to toggle." },
    { r: 5, t: "Voyage official store warranty includes zero bright dot guarantee for 3 years. Customer peace of mind is unmatched." },
    { r: 4, t: "Both premium DisplayPort 1.4 and HDMI 2.0 braided cables were included in the retail box. Clean integrated cable management." },
    { r: 1, t: "Courier delivered during heavy rainstorm, but double-boxed waterproof wrapping kept the internal packaging bone dry." },
    { r: 5, t: "Fast IPS liquid crystal response eliminates ghosting during high-speed camera pans in racing and tactical shooter games." },
    { r: 3, t: "Good 27-inch gaming monitor. Built-in speakers are basic, but display panel and ergonomic stand are exceptional." },
    { r: 5, t: "Clean three-sided frameless design looks gorgeous on desk. 1440p pixel density is the sweet spot for visual fidelity and performance." },
    { r: 4, t: "Anti-glare 3H matte surface treatment diffuses harsh window daylight without introducing rainbow graininess." },
    { r: 5, t: "Single-cable USB-C video, audio, and charging workflow is a productivity superpower. Highly recommended for creative pros." },
    { r: 4, t: "Sturdy metal base has compact footprint while keeping the 27-inch screen steady during typing." },
    { r: 2, t: "Stand has deep footprint, but VESA 100x100 mounting allowed me to attach it cleanly to a gas-spring monitor arm." },
    { r: 5, t: "Outstanding QHD 165Hz display. Vivid Fast IPS color accuracy, ultra-low input lag, and versatile USB-C docking." },
    { r: 4, t: "Smooth 165Hz refresh rate significantly reduces eye fatigue during long 12-hour software development sessions." },
    { r: 5, t: "High resolution, fast refresh rate, accurate colors, and top-tier build quality. Voyage UltraVision 27 is the complete package." },
    { r: 3, t: "Decent monitor for coding and gaming. Fluid 165Hz refresh rate and sharp QHD display." },
    { r: 5, t: "Five stars across the board. Voyage UltraVision 27 is the best monitor in its class!" },
  ]
};

const STEAM_TEMPLATES = {
  prod_001: [ // Baldur's Gate 3 (Audio immersion, Headphones, voice acting, RPG tactical gameplay)
    { r: 5, t: "210.4 hrs on record (Recommended). [Steam - Baldur's Gate 3] The orchestral soundtrack and voice acting by Neil Newbon (Astarion) sound mesmerizing on Voyage Horizon headphones. Spatial separation in the Shadow-Cursed Lands is chilling and atmospheric." },
    { r: 5, t: "184.2 hrs on record (Recommended). [Steam - Baldur's Gate 3] Act 3 runs great after Patch 7. Playing with high-res studio audio brings out every tavern conversation and battle spell acoustic in exquisite detail." },
    { r: 4, t: "142.1 hrs on record (Recommended). [Steam - Baldur's Gate 3] D&D 5e tactical combat is unmatched. Micro-managing party positioning and inventory feels crisp, and sound cues for stealth checks are clearly audible." },
    { r: 5, t: "310.8 hrs on record (Recommended). [Steam - Baldur's Gate 3] Winner of Game of the Year for a reason. 4-player co-op crossplay with friends with crystal clear voice callouts made our Honour Mode run legendary." },
    { r: 4, t: "98.5 hrs on record (Recommended). [Steam - Baldur's Gate 3] Story choices have genuine weight. Ambient audio of the Underdark with hybrid ANC on cuts out all real-world distractions." },
    { r: 3, t: "75.2 hrs on record (Recommended). [Steam - Baldur's Gate 3] Turn-based combat can feel slow if you prefer pure action, but the depth of spells, dialogue branches, and companion lore is monumental." },
    { r: 5, t: "250.0 hrs on record (Recommended). [Steam - Baldur's Gate 3] The voice acting across all 12 classes is cinematic perfection. Wearing comfortable over-ear headphones for 6-hour weekend sessions without ear fatigue." },
    { r: 2, t: "62.4 hrs on record (Not Recommended). [Steam - Baldur's Gate 3] Encountered an elevator bug in the Gauntlet of Shar that wiped two companions on Honour mode. Still a great game but honour mode bugs sting." },
    { r: 5, t: "190.3 hrs on record (Recommended). [Steam - Baldur's Gate 3] Borislav Slavov's soundtrack is a masterwork. Down by the River gave me literal chills through 40mm beryllium drivers." },
    { r: 4, t: "115.6 hrs on record (Recommended). [Steam - Baldur's Gate 3] Runs smoothly on PC at 1440p resolution. Tactical camera controls and spell radial management are intuitive." },
    { r: 5, t: "280.9 hrs on record (Recommended). [Steam - Baldur's Gate 3] One of the greatest RPGs ever made. The companion romance arcs, branching quest endings, and combat physics make every replay unique." },
    { r: 4, t: "88.4 hrs on record (Recommended). [Steam - Baldur's Gate 3] Karlach's emotional monologues hit so hard with clear vocal acoustics. Sound isolation lets you immerse fully into Faerûn." },
    { r: 1, t: "45.0 hrs on record (Not Recommended). [Steam - Baldur's Gate 3] Too much dialogue and inventory management for my taste, prefer action RPGs like Elden Ring. Great production value though." },
    { r: 5, t: "340.5 hrs on record (Recommended). [Steam - Baldur's Gate 3] Finished 3 full playthroughs! Combat encounter design in the House of Hope with Raphael singing his own boss theme is peak gaming history." },
    { r: 3, t: "105.2 hrs on record (Recommended). [Steam - Baldur's Gate 3] Performance in the Lower City has improved significantly with recent FSR updates. Deep D&D tactical depth." },
    { r: 5, t: "165.7 hrs on record (Recommended). [Steam - Baldur's Gate 3] Full controller support on Steam Deck is verified and works wonderfully. Spatial audio cues make finding hidden perception chests easy." },
    { r: 4, t: "128.9 hrs on record (Recommended). [Steam - Baldur's Gate 3] Incredible narrative freedom. Pushing enemies off cliffs with Eldritch Blast never gets old." },
    { r: 5, t: "225.1 hrs on record (Recommended). [Steam - Baldur's Gate 3] Rich cinematic storytelling, incredible character animations, and pristine sound design. 10/10 masterwork." },
    { r: 4, t: "92.0 hrs on record (Recommended). [Steam - Baldur's Gate 3] Tactical turn-based combat gives you time to think and plan elaborate elemental combos. Great audio dynamics." },
    { r: 2, t: "55.3 hrs on record (Not Recommended). [Steam - Baldur's Gate 3] Camera angles inside multi-floor buildings can be finicky when fighting on staircases." },
    { r: 5, t: "295.4 hrs on record (Recommended). [Steam - Baldur's Gate 3] Unprecedented freedom of choice. You can talk your way out of boss battles or solve quests in ways developers never anticipated." },
    { r: 4, t: "135.0 hrs on record (Recommended). [Steam - Baldur's Gate 3] Companion interactions feel so alive. Soundtrack dynamic mixing between quiet dialogue and explosive thunder spells is flawless." },
    { r: 5, t: "178.6 hrs on record (Recommended). [Steam - Baldur's Gate 3] Over 200 Game of the Year awards well deserved. A landmark achievement in PC gaming." },
    { r: 3, t: "82.1 hrs on record (Recommended). [Steam - Baldur's Gate 3] Solid tactical RPG with hours of content. Requires patience to learn D&D spell slot mechanics." },
    { r: 5, t: "360.2 hrs on record (Recommended). [Steam - Baldur's Gate 3] Absolute pinnacle of role-playing games. Faerûn feels like a living world with audio immersion dialed to perfection." },
  ],
  prod_002: [ // Black Myth: Wukong (Boss fights, streaming audio, mic callouts, UE5 visuals)
    { r: 5, t: "72.4 hrs on record (Recommended). [Steam - Black Myth: Wukong] Staff stance transitions and dodge timings are razor sharp. When streaming my Chapter 4 boss attempts on Discord, my squad commended the crystal clear voice pickup from my studio condenser mic." },
    { r: 5, t: "65.8 hrs on record (Recommended). [Steam - Black Myth: Wukong] Visually breathtaking in Unreal Engine 5. Boss roar acoustics, staff deflection clangs, and Chinese orchestral soundtrack sound thunderous and rich." },
    { r: 4, t: "54.2 hrs on record (Recommended). [Steam - Black Myth: Wukong] Combat transformations into Guangzhi and Red Boy add so much tactical versatility. Running at 1440p with DLSS frame generation is butter smooth." },
    { r: 5, t: "89.6 hrs on record (Recommended). [Steam - Black Myth: Wukong] Boss variety is astounding — over 80 unique boss encounters! The mythical Journey to the West lore is honored with breathtaking cinematic direction." },
    { r: 4, t: "48.1 hrs on record (Recommended). [Steam - Black Myth: Wukong] Excellent combat feel. Staff spin deflects incoming arrow volleys while charging up 4-focus heavy strikes. Dynamic voice audio in streams is clean." },
    { r: 3, t: "38.5 hrs on record (Recommended). [Steam - Black Myth: Wukong] Level design has some invisible walls in Chapter 3 snowy forest, but the boss battles and spectacle make up for exploration quirks." },
    { r: 5, t: "110.2 hrs on record (Recommended). [Steam - Black Myth: Wukong] Yellow Loong and Erlang Shen boss battles pushed my reflexes to the absolute limit. Victory felt intensely rewarding!" },
    { r: 2, t: "28.4 hrs on record (Not Recommended). [Steam - Black Myth: Wukong] Tiger Vanguard boss difficulty spike is brutal. Hitboxes on some grab attacks feel slightly lingering." },
    { r: 5, t: "95.0 hrs on record (Recommended). [Steam - Black Myth: Wukong] The art direction, character models, and Nanite geometry in UE5 set a new benchmark for modern action RPGs." },
    { r: 4, t: "62.3 hrs on record (Recommended). [Steam - Black Myth: Wukong] Fluid animation blending between Pillar Stance, Smash Stance, and Thrust Stance. Sound effects have intense visceral weight." },
    { r: 5, t: "125.7 hrs on record (Recommended). [Steam - Black Myth: Wukong] A monumental achievement for Game Science. The end of chapter stop-motion animated shorts are pure artistic genius." },
    { r: 4, t: "51.9 hrs on record (Recommended). [Steam - Black Myth: Wukong] Great performance on modern PC hardware. Streaming commentary was clear without keyboard clatter thanks to cardioid mic isolation." },
    { r: 1, t: "18.2 hrs on record (Not Recommended). [Steam - Black Myth: Wukong] Game crashed on startup until I verified files and updated GPU drivers. Ran fine after driver update." },
    { r: 5, t: "82.0 hrs on record (Recommended). [Steam - Black Myth: Wukong] Pluck of Many spell summoning monkey clones to swarm bosses while you charge heavy strike is the most satisfying power fantasy." },
    { r: 3, t: "44.6 hrs on record (Recommended). [Steam - Black Myth: Wukong] Good soulslike action RPG. Challenging boss fights with deep mythic lore." },
    { r: 5, t: "102.5 hrs on record (Recommended). [Steam - Black Myth: Wukong] Sound design on the wind sage and dragon bosses is acoustic mastery. High resolution audio reproduction brings it alive." },
    { r: 4, t: "58.0 hrs on record (Recommended). [Steam - Black Myth: Wukong] Perfect dodge slow-motion effect gives that split-second adrenaline rush to punish bosses." },
    { r: 5, t: "135.4 hrs on record (Recommended). [Steam - Black Myth: Wukong] Finished New Game+ with all mythical gourds and relics unlocked. One of the best action games of the decade!" },
    { r: 4, t: "49.3 hrs on record (Recommended). [Steam - Black Myth: Wukong] The gourd drink customization and spirit soul transformations keep build crafting fresh throughout all 6 chapters." },
    { r: 2, t: "32.1 hrs on record (Not Recommended). [Steam - Black Myth: Wukong] Lacks a mini-map which makes navigating the desert canyons in Chapter 2 confusing at times." },
    { r: 5, t: "91.8 hrs on record (Recommended). [Steam - Black Myth: Wukong] Phenomenal staff martial arts animations based on authentic Shaolin monk motion capture." },
    { r: 4, t: "60.5 hrs on record (Recommended). [Steam - Black Myth: Wukong] Voice acting in both original Chinese and English dub is top notch. Streaming to Twitch with clean studio audio." },
    { r: 5, t: "115.0 hrs on record (Recommended). [Steam - Black Myth: Wukong] Unbelievable visual fidelity, satisfying combat progression, and epic mythical scale. 10/10." },
    { r: 3, t: "41.0 hrs on record (Recommended). [Steam - Black Myth: Wukong] Demanding on GPU, but lowering volumetric fog provides smooth 60+ FPS on mid-range rigs." },
    { r: 5, t: "140.2 hrs on record (Recommended). [Steam - Black Myth: Wukong] Masterpiece. The Destined One's journey is an unforgettable gaming experience." },
  ],
  prod_003: [ // Cyberpunk 2077 (FPS mouse aim, 58g agility, Ray Tracing, Night City, gunplay)
    { r: 5, t: "220.8 hrs on record (Recommended). [Steam - Cyberpunk 2077] Night City gunplay with Sandevistan feels incredible with the Voyage Apex 58g mouse. Flicking revolver headshots at 1440p 165Hz has zero ghosting or delay." },
    { r: 5, t: "195.4 hrs on record (Recommended). [Steam - Cyberpunk 2077] Ray Tracing Overdrive path tracing transforms Night City into the most visually realistic metropolis in gaming history. Gunplay is tight, fluid, and intensely satisfying." },
    { r: 4, t: "140.2 hrs on record (Recommended). [Steam - Cyberpunk 2077] Phantom Liberty expansion is CD PROJEKT RED at their absolute best. Dogtown atmosphere is gritty and Idris Elba delivers an Oscar-worthy performance." },
    { r: 5, t: "310.5 hrs on record (Recommended). [Steam - Cyberpunk 2077] Update 2.1 fixed all early launch issues completely. Redesigned cyberware perks, vehicle combat, and working metro system make Night City feel alive." },
    { r: 4, t: "88.6 hrs on record (Recommended). [Steam - Cyberpunk 2077] Fast FPS aim with lightweight mouse optical clicks makes dash-and-slash Katana builds feel like playing a cybernetic ninja simulator." },
    { r: 3, t: "65.0 hrs on record (Recommended). [Steam - Cyberpunk 2077] Demanding on PC hardware with full ray tracing, but DLSS 3.5 frame generation keeps frame rates buttery above 100 FPS." },
    { r: 5, t: "260.0 hrs on record (Recommended). [Steam - Cyberpunk 2077] The emotional ending sequences with Johnny Silverhand (Keanu Reeves) stay with you long after credits roll. Incredible narrative depth." },
    { r: 2, t: "42.1 hrs on record (Not Recommended). [Steam - Cyberpunk 2077] Police AI still occasionally spawns slightly too fast in narrow alleys, though vastly improved over launch 1.0." },
    { r: 5, t: "185.3 hrs on record (Recommended). [Steam - Cyberpunk 2077] Sound design of weapon reloads, cyberware audio cues, and techno radio stations like Body Heat and Pacific Dreams is unmatched." },
    { r: 4, t: "112.9 hrs on record (Recommended). [Steam - Cyberpunk 2077] Netrunner hacking builds wiping entire enemy compounds through security cameras without firing a bullet is pure power fantasy." },
    { r: 5, t: "290.4 hrs on record (Recommended). [Steam - Cyberpunk 2077] 3 complete playthroughs as Nomad, Streetkid, and Corpo. Symmetrical 58g mouse tracking makes micro-aiming sniper scopes effortless." },
    { r: 4, t: "96.5 hrs on record (Recommended). [Steam - Cyberpunk 2077] Combat music by Marcin Przybyłowicz pulses with aggressive synth energy during MaxTac boss encounters." },
    { r: 1, t: "25.0 hrs on record (Not Recommended). [Steam - Cyberpunk 2077] Need a modern graphics card to really appreciate the visuals; on older GTX cards performance struggles." },
    { r: 5, t: "340.0 hrs on record (Recommended). [Steam - Cyberpunk 2077] Night City in neon rain with path traced reflections on wet asphalt is visual art. Best open world immersion on Steam." },
    { r: 3, t: "78.2 hrs on record (Recommended). [Steam - Cyberpunk 2077] Good RPG shooter. Gunplay is punchy, vehicle handling with high sensitivity mouse steering feels decent." },
    { r: 5, t: "160.8 hrs on record (Recommended). [Steam - Cyberpunk 2077] Steam Deck preset runs at a solid 40 FPS. Cross-progression cloud saves between desktop PC and Deck work like a charm." },
    { r: 4, t: "130.1 hrs on record (Recommended). [Steam - Cyberpunk 2077] Smart weapons curving tracking bullets around cover while dashing mid-air is pure sci-fi adrenaline." },
    { r: 5, t: "245.7 hrs on record (Recommended). [Steam - Cyberpunk 2077] CDPR redeemed themselves completely with Update 2.0 and Phantom Liberty. One of the greatest action RPGs ever crafted." },
    { r: 4, t: "105.4 hrs on record (Recommended). [Steam - Cyberpunk 2077] Gorilla arms melee build tearing open locked security doors and throwing enemies across the room is hilarious." },
    { r: 2, t: "50.2 hrs on record (Not Recommended). [Steam - Cyberpunk 2077] Side gigs can feel slightly repetitive if you try to 100% clear the map in Watson early on." },
    { r: 5, t: "275.9 hrs on record (Recommended). [Steam - Cyberpunk 2077] The writing in character-driven side quests like River Ward and Judy Alvarez sets an industry gold standard." },
    { r: 4, t: "122.0 hrs on record (Recommended). [Steam - Cyberpunk 2077] Fluid mouse aim tracking at 1000Hz polling rate makes rapid target acquisition in shootout arenas feel natural." },
    { r: 5, t: "320.6 hrs on record (Recommended). [Steam - Cyberpunk 2077] An absolute masterpiece of cyberpunk worldbuilding, memorable characters, and exhilarating combat." },
    { r: 3, t: "68.4 hrs on record (Recommended). [Steam - Cyberpunk 2077] Great story and atmosphere. Driving takes a bit of practice to master." },
    { r: 5, t: "380.1 hrs on record (Recommended). [Steam - Cyberpunk 2077] Night City will forever hold a special place in gaming history. 10/10 must-play title." },
  ],
  prod_004: [ // Elden Ring (165Hz Monitor, 1ms response, boss fights, HDR visuals, FromSoft)
    { r: 5, t: "340.2 hrs on record (Recommended). [Steam - Elden Ring] Shadow of the Erdtree boss fights require split-second reaction. 1ms response time on my 165Hz IPS monitor completely eliminates ghosting and made defeating Consort Radahn possible." },
    { r: 5, t: "295.6 hrs on record (Recommended). [Steam - Elden Ring] Exploring Leyndell Royal Capital and the Haligtree for the first time is an unmatched gaming memory. FromSoftware's world design is legendary." },
    { r: 4, t: "185.0 hrs on record (Recommended). [Steam - Elden Ring] Peak open world exploration. You see a colossal structure on the horizon, and hours later you are exploring its deepest subterranean depths." },
    { r: 5, t: "420.5 hrs on record (Recommended). [Steam - Elden Ring] Over 400 hours and still discovering secret caves and questlines! Golden vistas of Altus Plateau look breathtaking with HDR color depth." },
    { r: 4, t: "125.4 hrs on record (Recommended). [Steam - Elden Ring] Challenging but deeply rewarding boss mechanics. Fluid combat dodging with zero display latency is essential for parrying Crucible Knights." },
    { r: 3, t: "90.2 hrs on record (Recommended). [Steam - Elden Ring] PC version frame rate is capped at 60 FPS natively, but using the unlocker mod at 165Hz QHD makes combat feel modern and silky smooth." },
    { r: 5, t: "310.8 hrs on record (Recommended). [Steam - Elden Ring] The build variety with colossal swords, sorceries, incantations, and bleed katanas allows infinite replay value across New Game cycles." },
    { r: 2, t: "48.1 hrs on record (Not Recommended). [Steam - Elden Ring] Malenia Waterfowl Dance attack hitbox requires hyper-specific dodge timing that feels slightly overtuned for casual players." },
    { r: 5, t: "255.3 hrs on record (Recommended). [Steam - Elden Ring] Orchestral boss fight tracks during Radagon of the Golden Order and Starscourge Radahn deliver pure adrenaline." },
    { r: 4, t: "160.7 hrs on record (Recommended). [Steam - Elden Ring] Torrent mount mechanics make traversing the sprawling Lands Between fast and enjoyable. Jump attacks add great verticality to combat." },
    { r: 5, t: "380.0 hrs on record (Recommended). [Steam - Elden Ring] Game of the Year 2022 and Shadow of the Erdtree expansion cemented this as one of the greatest games ever conceived by human minds." },
    { r: 4, t: "115.0 hrs on record (Recommended). [Steam - Elden Ring] Rich environmental storytelling without intrusive quest markers cluttering your screen. Trust in player curiosity." },
    { r: 1, t: "20.4 hrs on record (Not Recommended). [Steam - Elden Ring] Lost 50,000 runes to gravity falling off a cliff in Caelid. Infuriating difficulty if you don't have patience." },
    { r: 5, t: "450.0 hrs on record (Recommended). [Steam - Elden Ring] The scale of the underground Siofra River and Nokron Eternal City when taking the well elevator for the first time blew my mind." },
    { r: 3, t: "85.6 hrs on record (Recommended). [Steam - Elden Ring] Hard game that respects your intelligence. Be prepared to die and learn boss attack patterns." },
    { r: 5, t: "190.2 hrs on record (Recommended). [Steam - Elden Ring] Verified on Steam Deck and runs great. Fast IPS monitor color reproduction makes the Erdtree glow majestically." },
    { r: 4, t: "145.8 hrs on record (Recommended). [Steam - Elden Ring] Weapon ashes of war skill customization gives standard weapons unique magical abilities and affinity scaling." },
    { r: 5, t: "270.3 hrs on record (Recommended). [Steam - Elden Ring] Co-op summoning with friends to tackle challenging dungeon bosses is some of the most fun I've had in gaming." },
    { r: 4, t: "105.1 hrs on record (Recommended). [Steam - Elden Ring] Sound design audio cues for boss windups allow dodging purely on acoustic timing. Very well engineered." },
    { r: 2, t: "58.0 hrs on record (Not Recommended). [Steam - Elden Ring] Duo boss fights like Godskin Duo can feel frustrating for solo melee builds without spirit ashes." },
    { r: 5, t: "365.4 hrs on record (Recommended). [Steam - Elden Ring] Miyazaki and George R.R. Martin created a mythos that will be studied and celebrated for decades. 10/10 masterpiece." },
    { r: 4, t: "138.9 hrs on record (Recommended). [Steam - Elden Ring] Legacy dungeons like Stormveil Castle have intricate vertical shortcuts and hidden jump routes. Masterclass in level design." },
    { r: 5, t: "410.2 hrs on record (Recommended). [Steam - Elden Ring] The ultimate dark fantasy action RPG. Unmatched atmosphere, colossal world scale, and thrilling boss battles." },
    { r: 3, t: "72.0 hrs on record (Recommended). [Steam - Elden Ring] Demanding combat that tests your composure. Highly rewarding once you master roll timings." },
    { r: 5, t: "480.0 hrs on record (Recommended). [Steam - Elden Ring] Rise, Tarnished. An absolute triumph of gaming art and design. Essential play for every gamer." },
  ]
};

// ── User ID generation helpers ──
const USERNAMES = [
  'arjun_tech88', 'rohit_sharma_99', 'priya_audio', 'karthik_r24', 'ananya_deshmukh',
  'vikram_aditya', 'sneha_mallya', 'rahul_verma01', 'deepak_kumar_in', 'pooja_nair',
  'suresh_raina_fan', 'neha_patel_dev', 'amitabh_k', 'divya_krishnan', 'siddharth_m',
  'tanvi_soundlab', 'manoj_bajpayee', 'alok_nath_tech', 'kavya_s', 'harsh_vardhan',
  'aditi_rao_92', 'chetan_bhagat_fan', 'varun_dhawan_fan', 'shreya_ghoshal_fan', 'nikhil_chinapa',
  'gamer_raghav', 'tarnished_blade', 'nightcity_v', 'monkey_king_wukong', 'shadow_heart_bg3',
  'cyber_samurai', 'elden_lord_99', 'astarion_fangirl', 'wukong_staff_master', 'silverhand_rocker',
  'pixel_perfect_fps', 'beast_slayer_24', 'clutch_god_aim', 'audiophile_delhi', 'bangalore_coder',
  'mumbai_streamer', 'pune_esports_hub', 'hyderabad_techie', 'chennai_gamer', 'kolkata_sound',
  'desiracer_99', 'tech_guru_india', 'pro_gamer_ashish', 'sound_engineer_sam', 'gadget_freak_amit'
];

function getRandomUser(idx, platform) {
  const base = USERNAMES[idx % USERNAMES.length];
  if (platform === 'brand') {
    return `${base}@voyage.tech`;
  } else if (platform === 'amazon') {
    return `${base}@amazon.buyer.in`;
  } else if (platform === 'flipkart') {
    return `${base}@flipkart.in`;
  } else if (platform === 'jiomart') {
    return `${base}@jio.com`;
  } else {
    return base; // Steam persona
  }
}

function getRandomTimestamp(idx) {
  // Distribute over past 12 months up to Oct 2026
  const baseTime = new Date('2026-10-25T12:00:00.000Z').getTime();
  const offsetDays = (idx * 0.72) % 360;
  const time = new Date(baseTime - offsetDays * 86400000);
  return time.toISOString();
}

function generateAll500Reviews() {
  const reviews = [];
  let globalIdx = 0;

  // 1. Amazon (100 reviews)
  ['prod_001', 'prod_002', 'prod_003', 'prod_004'].forEach(pid => {
    const templates = AMAZON_TEMPLATES[pid];
    templates.forEach((tmpl, i) => {
      reviews.push({
        product_id: pid,
        platform: 'amazon',
        review_text: tmpl.t,
        transcript: null,
        rating: tmpl.r,
        user_id: getRandomUser(globalIdx, 'amazon'),
        media_type: 'none',
        timestamp: getRandomTimestamp(globalIdx++)
      });
    });
  });

  // 2. Flipkart (100 reviews)
  ['prod_001', 'prod_002', 'prod_003', 'prod_004'].forEach(pid => {
    const templates = FLIPKART_TEMPLATES[pid];
    templates.forEach((tmpl, i) => {
      reviews.push({
        product_id: pid,
        platform: 'flipkart',
        review_text: tmpl.t,
        transcript: null,
        rating: tmpl.r,
        user_id: getRandomUser(globalIdx, 'flipkart'),
        media_type: 'none',
        timestamp: getRandomTimestamp(globalIdx++)
      });
    });
  });

  // 3. JioMart (100 reviews)
  ['prod_001', 'prod_002', 'prod_003', 'prod_004'].forEach(pid => {
    const templates = JIOMART_TEMPLATES[pid];
    templates.forEach((tmpl, i) => {
      reviews.push({
        product_id: pid,
        platform: 'jiomart',
        review_text: tmpl.t,
        transcript: null,
        rating: tmpl.r,
        user_id: getRandomUser(globalIdx, 'jiomart'),
        media_type: 'none',
        timestamp: getRandomTimestamp(globalIdx++)
      });
    });
  });

  // 4. Voyage Brand Store (100 reviews)
  ['prod_001', 'prod_002', 'prod_003', 'prod_004'].forEach(pid => {
    const templates = BRAND_TEMPLATES[pid];
    templates.forEach((tmpl, i) => {
      reviews.push({
        product_id: pid,
        platform: 'brand',
        review_text: tmpl.t,
        transcript: null,
        rating: tmpl.r,
        user_id: getRandomUser(globalIdx, 'brand'),
        media_type: 'none',
        timestamp: getRandomTimestamp(globalIdx++)
      });
    });
  });

  // 5. Steam (100 reviews, stored with platform: 'brand' in Sequelize enum, prefixed [Steam - <Game>])
  ['prod_001', 'prod_002', 'prod_003', 'prod_004'].forEach(pid => {
    const templates = STEAM_TEMPLATES[pid];
    templates.forEach((tmpl, i) => {
      reviews.push({
        product_id: pid,
        platform: 'brand',
        review_text: tmpl.t,
        transcript: null,
        rating: tmpl.r,
        user_id: getRandomUser(globalIdx, 'steam'),
        media_type: 'none',
        timestamp: getRandomTimestamp(globalIdx++)
      });
    });
  });

  return reviews;
}

const all500 = generateAll500Reviews();
console.log(`Generated total reviews: ${all500.length}`);

// Breakdown counts
const breakdown = {};
all500.forEach(r => {
  let plat = r.platform;
  if (plat === 'brand' && r.review_text.startsWith('[Steam')) {
    plat = 'steam';
  }
  const key = `${plat} : ${r.product_id}`;
  breakdown[key] = (breakdown[key] || 0) + 1;
});
console.log('Breakdown by platform & product:');
console.table(breakdown);

// Write to files
// 1. reviews-data.js for simulation offline bootstrap
const reviewsDataJsContent = `(function() { window.REVIEWS_DATA = ${JSON.stringify(all500, null, 2)}; })();\n`;
fs.writeFileSync(path.join(__dirname, 'reviews-data.js'), reviewsDataJsContent, 'utf8');
fs.writeFileSync(path.join(__dirname, '..', '..', 'PRISM FRONTEND', 'simulation', 'reviews-data.js'), reviewsDataJsContent, 'utf8');

// 2. seed-reviews.json
const seedReviewsJsonContent = JSON.stringify({
  company: "Voyage",
  products: [
    { product_id: "prod_001", name: "Voyage Horizon ANC", category: "Headphones" },
    { product_id: "prod_002", name: "Voyage StreamCast Pro", category: "Microphones" },
    { product_id: "prod_003", name: "Voyage Apex Wireless", category: "Gaming Mouse" },
    { product_id: "prod_004", name: "Voyage UltraVision 27\"", category: "Gaming Monitors" }
  ],
  reviews: all500
}, null, 2);

fs.writeFileSync(path.join(__dirname, 'seed-reviews.json'), seedReviewsJsonContent, 'utf8');
fs.writeFileSync(path.join(__dirname, '..', '..', 'PRISM FRONTEND', 'simulation', 'seed-reviews.json'), seedReviewsJsonContent, 'utf8');

console.log('Successfully wrote reviews-data.js and seed-reviews.json in both simulation folders!');
