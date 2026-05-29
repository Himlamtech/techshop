import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import dotenv from "dotenv";
import { GoogleGenAI } from "@google/genai";

dotenv.config();

const app = express();
const PORT = parseInt(process.env.PORT || "5173", 10);

// Parse JSON bodies
app.use(express.json());

// Initialize Gemini SDK lazily, as instructed in Guidelines (fails gracefully on missing key)
let aiClient: GoogleGenAI | null = null;
const MODEL_NAME = "gemini-3.5-flash";

function getGeminiClient(): GoogleGenAI {
  if (!aiClient) {
    const key = process.env.GEMINI_API_KEY;
    if (!key) {
      console.warn("WARNING: GEMINI_API_KEY is not defined. Using mock fallback mode for Gemini API calls.");
      // We will handle key being missing elegantly so the server doesn't crash, but throws descriptive mock results
    }
    aiClient = new GoogleGenAI({
      apiKey: key || "MOCK_KEY",
      httpOptions: {
        headers: {
          "User-Agent": "aistudio-build",
        },
      },
    });
  }
  return aiClient;
}

// API Routes
app.get("/api/health", (req, res) => {
  res.json({ status: "ok", usingRealGemini: !!process.env.GEMINI_API_KEY });
});

// Product Q&A Endpoint
app.post("/api/product-qa", async (req, res) => {
  const { product, question } = req.body;
  if (!product || !question) {
    return res.status(400).json({ error: "Missing product or question parameter" });
  }

  // Gracefully check for real API key
  const key = process.env.GEMINI_API_KEY;
  if (!key) {
    // Elegant fallback simulation if no key is supplied
    setTimeout(() => {
      res.json({
        answer: `[DEMO MODE - GEMINI KEY NOT PROVIDED] As an AI, I analyzed **${product.name}** to answer your question: "${question}". Based on its official specs (Price: $${product.price}, Category: ${product.category}), here's what you need to know:
1. **Dynamic Capabilities:** It highlights features like ${product.features[0] || 'advanced premium components'} and ${product.features[1] || 'durable styling'}.
2. **Compatibility:** Its ${product.specs[0]?.label || 'Specs'} is rated at "${product.specs[0]?.value || 'Superior'}" making it ideal for high-performance setups.
3. **Verdict:** This is a stellar choice for users seeking efficiency in their daily flow. Feel free to supply custom API Secret keys in Settings if you'd like live full-scale analysis!`,
      });
    }, 1200);
    return;
  }

  try {
    const ai = getGeminiClient();
    const systemInstruction = `You are a friendly, highly knowledgeable tech sales consultant at Aether Tech Shop. 
An customer is asking a about a specific product in our store: "${product.name}".
Use the following product specifications to answer their question exhaustively and professionally:
Name: ${product.name}
Price: $${product.price}
Category: ${product.category}
Rating: ${product.rating} / 5 (${product.reviewsCount} reviews)
Description: ${product.description}
Core Highlight features:
${product.features.map((f: string) => `- ${f}`).join("\n")}
Technical details:
${product.specs.map((s: any) => `- ${s.label}: ${s.value}`).join("\n")}

Respond in clear Markdown. Be objective, honest, enthusiastic, and target their use-case directly. Do not make up facts.`;

    const response = await ai.models.generateContent({
      model: MODEL_NAME,
      contents: question,
      config: {
        systemInstruction,
        temperature: 0.7,
      },
    });

    res.json({ answer: response.text });
  } catch (error: any) {
    console.error("Gemini Product QA Error:", error);
    res.status(500).json({ error: error.message || "Failed to generate AI response" });
  }
});

// Side-by-Side Product Comparison Generator
app.post("/api/product-compare", async (req, res) => {
  const { productA, productB } = req.body;
  if (!productA || !productB) {
    return res.status(400).json({ error: "Missing productA or productB parameter" });
  }

  const key = process.env.GEMINI_API_KEY;
  if (!key) {
    // Elegant mock fallback
    setTimeout(() => {
      res.json({
        report: `### AI Comparison: ${productA.name} vs ${productB.name} (DEMO MODE)

| Metric | ${productA.name} | ${productB.name} |
| :--- | :--- | :--- |
| **Price** | $${productA.price} | $${productB.price} |
| **Category** | ${productA.category} | ${productB.category} |
| **Rating** | ${productA.rating} ★ | ${productB.rating} ★ |
| **Core Edge** | ${productA.features[0] || 'Luxury build'} | ${productB.features[0] || 'Next-gen design'} |

#### 🏆 Key Differences & Breakdown
1. **Financial Choice:** ${productA.name} costs $${productA.price} while ${productB.name} sits at $${productB.price}, making **${productA.price < productB.price ? productA.name : productB.name}** the budget-friendly path.
2. **Target Audience:** ${productA.name} targets those looking for *"${productA.tag}"*, whereas ${productB.name} excels in *"${productB.tag}"*.
3. **Technical Build:** ${productA.name} features highlights like *"${productA.specs[0]?.value || 'Custom Spec'}"* compared to ${productB.name}'s *"${productB.specs[0]?.value || 'Alternative Spec'}"*.

---
#### 💡 AI Recommendation Verdict
* **Choose ${productA.name} if:** You appreciate titanium high-efficiency materials, silent operation, and long battery thresholds.
* **Choose ${productB.name} if:** You are seeking absolute cutting-edge technology, dense structural stability, and rich haptic details to streamline creative output.`,
      });
    }, 1500);
    return;
  }

  try {
    const ai = getGeminiClient();
    const systemInstruction = `You are an expert tech product analyst. 
Compare the technical specs, pricing, and capabilities of the two tech products listed below. 
Generate a beautifully formatted side-by-side comparison report in Markdown.
The report MUST contain:
- A clean markdown comparison table comparing key metrics (Price, Rating, Primary Feature, Key Spec)
- A "Key Distinct Differences" breakdown listing 3-4 points of contrast
- Clear recommendation sectors: "Who should choose Product A" and "Who should choose Product B"
- A final concise AI Verdict.

Product A Info:
- Name: ${productA.name}
- Price: $${productA.price}
- Category: ${productA.category}
- Rating: ${productA.rating}
- Tagline: ${productA.tag}
- Description: ${productA.description}
- Features: ${productA.features.join(", ")}
- Specs: ${productA.specs.map((s: any) => `${s.label}: ${s.value}`).join(", ")}

Product B Info:
- Name: ${productB.name}
- Price: $${productB.price}
- Category: ${productB.category}
- Rating: ${productB.rating}
- Tagline: ${productB.tag}
- Description: ${productB.description}
- Features: ${productB.features.join(", ")}
- Specs: ${productB.specs.map((s: any) => `${s.label}: ${s.value}`).join(", ")}`;

    const response = await ai.models.generateContent({
      model: MODEL_NAME,
      contents: "Generate comparison report.",
      config: {
        systemInstruction,
        temperature: 0.8,
      },
    });

    res.json({ report: response.text });
  } catch (error: any) {
    console.error("Gemini Product Compare Error:", error);
    res.status(500).json({ error: error.message || "Failed to generate AI comparison" });
  }
});

// Full-Scale AI Chatbot Assistant Endpoint
app.post("/api/chat", async (req, res) => {
  const { messages, selectedProductId } = req.body;
  if (!messages || !Array.isArray(messages)) {
    return res.status(400).json({ error: "Missing or invalid messages parameter" });
  }

  // Grab the latest user message
  const userMessages = messages.filter((m: any) => m.sender === "user");
  const latestMessage = userMessages[userMessages.length - 1]?.text || "";

  const key = process.env.GEMINI_API_KEY;
  if (!key) {
    // Elegant simulated fallback
    setTimeout(() => {
      let responseText = `[DEMO MODE] Thanks for asking! I'm here to act as your Aether Tech Personal Shopper. Currently, we have some fantastic devices available, including the **Aether Glass Pro** ($899), the **Quantum Sound H1** ($349), and the developers' favorite **Nexus Key Zero** ($219). Let me know if you would like me to compare them or give you advice!`;

      const lowerMsg = latestMessage.toLowerCase();
      if (lowerMsg.includes("recommend") || lowerMsg.includes("suggest") || lowerMsg.includes("buy")) {
        responseText = `Based on current tech trends, I highly suggest checking out the **Aether Glass Pro** if you want elite wearable AR capabilities, or the **Quantum Sound H1** headphones for industry-leading 360-degree spatial silence. What are your primary goals for these gadgets?`;
      } else if (lowerMsg.includes("keyboard") || lowerMsg.includes("nexus") || lowerMsg.includes("type")) {
        responseText = `Ah, the **Nexus Key Zero**! That is our top mechanical peripheral featuring solid CNC bead-blasted aluminum housing and linear Hall Effect switches. If you do a lot of coding or gaming, its customizable 0.1mm actuation is revolutionary.`;
      } else if (lowerMsg.includes("glass") || lowerMsg.includes("ar") || lowerMsg.includes("lens")) {
        responseText = `The **Aether Glass Pro** ($899) is our premium titanium mixed-reality HUD. It provides real-time AI translation overlays and works continuous bone conduction audio. Highly recommended for travelers and developers!`;
      }

      res.json({ text: responseText });
    }, 1200);
    return;
  }

  try {
    const ai = getGeminiClient();

    // Construct formatting and store catalogue guidelines
    const modelSystemInstruction = `You are the primary tech expert AI shopping assistant for AETHER Tech Shop, a premium, minimalist retailer for futuristic, extremely high-end hardware.
You are warm, intelligent, objective, and expert-level. You speak with clear, supportive enthusiasm and avoid buzzwords.
You help customers choose the ideal gadget based on their lifestyle, budget, or productivity needs.
If asked about items not in our catalog, gently redirect them to Aether alternatives or answer with technical knowledge while showcasing the Aether equivalent.

Catalog Overview of products currently in stock:
1. **Aether Glass Pro** ($899) - Augmented Reality Titanium HUD Spectacles. Custom bone conduction, real-time translations.
2. **Quantum Sound H1** ($349) - ANC wireless headphones. 40mm Beryllium High Definition, 45dB noise block, 48hr battery.
3. **Chrono Dial T1** ($499) - Ultra-rugged Grade-5 Titanium Sapphire Smartwatch. Dual satellite tracking, continuous biosensing, solar charging crystal (21 days).
4. **Nexus Key Zero** ($219) - Compact 75% CNC mechanical keyboard. Hall Effect magnetic linear switches with custom actuation, rapid trigger, aluminum build.
5. **Aura Beam Q1** ($1299) - Triple Laser 4K Projector. 2200 ANSI Lumens, Dolby Audio speakers, intelligent digital keystone.
6. **Core Pad Space** ($159) - Pressure-sensitive spatial haptic glass trackpad. Ergonomic multi-angle kickstands for wrist relief, OLED dial bar.

If a specific product is currently selected and highlighted by the user (ID: ${selectedProductId || "(none)"}), make sure to lean towards showcasing it if it fits their query.
Use standard clean Markdown formatting in responses. Always keep it engaging!`;

    // Flatten history into Gemini-SDK expected message structure or simple continuous chat
    // For simplicity and extreme robustness utilizing gemini-3.5-flash:
    // Format previous conversation into a cohesive text prompt representation
    const formattedPrompt = messages.map((m: any) => `${m.sender === "user" ? "Customer" : "AI Shopping Expert"}: ${m.text}`).join("\n") + "\nAI Shopping Expert:";

    const response = await ai.models.generateContent({
      model: MODEL_NAME,
      contents: formattedPrompt,
      config: {
        systemInstruction: modelSystemInstruction,
        temperature: 0.75,
      },
    });

    res.json({ text: response.text });
  } catch (error: any) {
    console.error("Gemini Chat助理 Error:", error);
    res.status(500).json({ error: error.message || "Something went wrong in the AI engine" });
  }
});

// Configure Vite middleware or static serving
async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server successfully operating on http://0.0.0.0:${PORT}`);
  });
}

startServer();
