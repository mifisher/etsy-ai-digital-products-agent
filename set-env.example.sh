# Example environment config. Copy to set-env.sh and fill in your own values:
#   cp set-env.example.sh set-env.sh && source set-env.sh
# set-env.sh is git-ignored — NEVER commit real keys.

# --- Etsy API (for OAuth + draft listing upload) ----------------------------
export ETSY_CLIENT_ID="your-etsy-keystring"
export ETSY_CLIENT_SECRET="your-etsy-shared-secret"
export ETSY_SHOP_ID="your-numeric-shop-id"
export ETSY_REDIRECT_URI="https://localhost:3000/oauth/callback"

# --- LLM generation (optional; pip install openai) --------------------------
export ETSY_USE_LLM="1"

# Moonshot (Kimi) — OpenAI-compatible:
export ETSY_LLM_PROVIDER="moonshot"
export MOONSHOT_API_KEY="your-moonshot-key"
# export ETSY_LLM_MODEL="kimi-k2-0711-preview"
# export MOONSHOT_BASE_URL="https://api.moonshot.ai/v1"

# ...or OpenAI instead:
# export ETSY_LLM_PROVIDER="openai"
# export OPENAI_API_KEY="your-openai-key"
