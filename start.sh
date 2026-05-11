#!/bin/bash
# Start both bots in parallel

echo "🚀 Starting Bot 1 (Monitoring)..."
python -u tazkarti_bot.py &
BOT1_PID=$!

echo "🚀 Starting Bot 2 (Booking)..."
python -u -m booking_bot.main &
BOT2_PID=$!

echo "✅ Both bots running! (PIDs: $BOT1_PID, $BOT2_PID)"

# Wait for either to exit
wait -n $BOT1_PID $BOT2_PID

# If one dies, kill the other and exit
echo "❌ One of the bots crashed! Shutting down..."
kill $BOT1_PID $BOT2_PID 2>/dev/null
exit 1
