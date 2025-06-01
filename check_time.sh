#!/bin/bash

# Define time slots (in 24-hour format)
time_slots=("08:00" "14:00" "22:00" "02:00")

# Get the current time in seconds since midnight
current_time=$(date +"%H:%M")

# Loop through the defined time slots
for slot in "${time_slots[@]}"; do
    # Convert the current time and slot time to minutes since midnight
    current_minutes=$((10#$(echo $current_time | awk -F: '{print ($1 * 60) + $2}')))
    slot_minutes=$((10#$(echo $slot | awk -F: '{print ($1 * 60) + $2}')))
    slot_end_minutes=$((slot_minutes + 60))  # Add 60 minutes for 1-hour range

    # Check if the current time in minutes is within the range
    if [ "$current_minutes" -ge "$slot_minutes" ] && [ "$current_minutes" -lt "$slot_end_minutes" ]; then
        # echo "Current time is within the range of $slot to $(printf '%02d:%02d' $((slot_end_minutes / 60)) $((slot_end_minutes % 60)))"
        echo "run script"

        # Exit after execution
        exit 0
    fi
done

# If no match, output a message
echo "No matching time slot for now. Current time: $current_time"
