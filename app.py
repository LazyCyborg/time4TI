import streamlit as st
import pandas as pd
import datetime
import time

# --- Initialize Session State ---
# This needs to run first on every execution to ensure state exists
if 'Number of cycles' not in st.session_state:
    st.session_state['Number of cycles']= 0
    st.session_state['Target number of cycles'] = 0

if 'Frequency' not in st.session_state:
    st.session_state['Carrier frequency 1'] = 0
    st.session_state['Carrier frequency 2'] = 0
    st.session_state['Modulating frequency'] = 0

if 'timer_running' not in st.session_state:
    st.session_state.timer_running = False
    st.session_state.end_time = None
    st.session_state.vpp_value = 0.0
    st.session_state.target_vpp = 0.0
    st.session_state.last_ramp_second = -1

if 'paused' not in st.session_state:
    st.session_state.paused = False
    st.session_state.time_remaining_on_pause = None # Store remaining seconds when paused

if 'quit_early' not in st.session_state:
    st.session_state.quit_early = False # Flag to indicate if session was quit

if 'session_summary' not in st.session_state:
    st.session_state.session_summary = None

st.title('Time4TI ⚡️')
st.markdown("Timer and logging app for classic temporal interference stimulation experiments. Currently only set to handle a two channel setup.")

st.metric("Number of cycles", f"{st.session_state['Number of cycles']}")

# --- Main Display Logic ---

if not st.session_state.timer_running:
    # --- STATE: Timer Not Running (Initial or Finished) ---

    # --- Display Summary if available ---
    if st.session_state.session_summary is not None:
        st.write("--- Session Summary ---")
        if st.session_state.quit_early:
            st.warning("Session Quit Early!")
        else:
            st.success("Session Finished! ✅")
        st.metric("Final Amplitude (Vpp)", f"{st.session_state.vpp_value:.1f}")
        st.dataframe(st.session_state.session_summary)
        st.divider() # Visual separation

        # Button to clear summary and allow new configuration
        if st.button("Configure New Session", key="clear_summary"):
             st.session_state.end_time = None # Essential to hide summary next time
             st.session_state.session_summary = None
             st.session_state.quit_early = False # Reset quit flag
             st.rerun()

    # --- User Input Form ---
    # Show form only if no end_time exists (initial state or after clearing summary)
    if st.session_state.end_time is None:
        st.info("Configure and press 'Start Session'.")
        with st.form("timer_form"):
            st.write("Configure the TI session:")
            minutes_val = st.slider(
                "Duration per cycle (minutes)",
                min_value=1, max_value=120, value=5, key="minutes_slider"
            )
            vpp_val = st.slider(
                "Target Amplitude (Vpp)",
                min_value=0.0, max_value=6.0, value=4.0, step=0.1, key="vpp_slider"
            )

            carr_freq_1 = st.number_input(
                "Channel 1 carrier frequency (Hz)",
                min_value=0, max_value=20000, value=8000, step=1, key="carr_1"
            )
            st.session_state['Carrier frequency 1'] = carr_freq_1

            carr_freq_2 = st.number_input(
                "Channel 2 carrier frequency (Hz)",
                min_value=0, max_value=20000, value=8130, step=1, key="carr_2"
            )

            if carr_freq_2 - carr_freq_1 < 0:
                st.warning("Modulating frequencu cannot be negative. Adjust frequencies accordingly.")

            st.session_state['Carrier frequency 2'] = carr_freq_2

            st.write(f"Modulating frequency = {carr_freq_2 - carr_freq_1} Hz")

            st.session_state['Modulating frequency'] = carr_freq_2 - carr_freq_1

            target_n_cycles = st.number_input("Set target number of cycles", min_value=1, max_value=120)
            st.write("Selected number of cycles ", target_n_cycles)
            ramp_speed = st.number_input("Ramp Speed", value=0.1, min_value=0.01, max_value=0.1)

            updated = st.form_submit_button("Update", icon="🔄")

            if updated:
                st.session_state['Target number of cycles'] = target_n_cycles
                st.session_state.timer_running = False
                st.session_state.paused = False
                st.session_state.quit_early = False
                st.session_state.session_summary = None
                st.session_state.target_vpp = vpp_val,
                st.session_state['Modulating frequency'] = carr_freq_2 - carr_freq_1,
                st.session_state.ramp_speed = ramp_speed
                st.rerun()


            st.text('Ramp ↑ will appear on even seconds remaining.') # Explain ramp logic
            submitted = st.form_submit_button("Start Session", icon="🚀")

            if submitted:
                st.session_state['Target number of cycles'] = target_n_cycles
                st.session_state.timer_running = True
                st.session_state.paused = False
                st.session_state.quit_early = False
                st.session_state.session_summary = None
                duration = datetime.timedelta(minutes=minutes_val)
                st.session_state.end_time = datetime.datetime.now() + duration
                st.session_state.target_vpp = vpp_val
                st.session_state.vpp_value = 0.0
                st.session_state.last_ramp_second = -1
                st.session_state.ramp_speed = ramp_speed
                st.rerun()



elif st.session_state.timer_running:
    # --- STATE: Timer Running (or Paused) ---

    secs_remaining_total = 0 # Initialize

    if not st.session_state.paused:
        # --- Timer Actively Running ---
        if st.session_state.end_time is None:
            # Safety check
            st.error("Error: Timer running but end time not set.")
            st.session_state.timer_running = False
            st.rerun()
        else:
            time_remaining = st.session_state.end_time - datetime.datetime.now()
            secs_remaining_total = int(time_remaining.total_seconds())

            if secs_remaining_total < 0:
                # --- Timer Finished Naturally ---
                st.session_state.timer_running = False
                st.session_state.quit_early = False # Didn't quit
                st.session_state['Number of cycles'] += 1

                # Prepare summary data
                d = {
                    'Status': ['Completed'],
                    'Target Cycles': [st.session_state['Target number of cycles']],
                    'Completed Cycles': [st.session_state['Number of cycles']],
                    'Carrier frequency 1': st.session_state['Carrier frequency 1'],
                    'Carrier frequency 2': st.session_state['Carrier frequency 2'],
                    'Modulating frequency': st.session_state['Modulating frequency'],
                    'Target Vpp': [st.session_state.target_vpp],
                    'Final Vpp': [round(st.session_state.vpp_value, 1)]
                }
                st.session_state.session_summary = pd.DataFrame(d)
                df = pd.DataFrame(data=d)
                @st.cache_data
                def convert_for_download(df):
                    return df.to_csv().encode("utf-8")

                csv = convert_for_download(df)
                st.download_button('Download data summary', csv, file_name="TI_session_summary.csv")
                st.rerun() # Go to the 'not running' state to display summary
            else:
                # --- Timer Ticking: Display Update ---
                mm = secs_remaining_total // 60
                ss = secs_remaining_total % 60
                st.metric("Time Remaining", f"{mm:02d}:{ss:02d}")
                ramp_message_placeholder = st.empty()

                # Ramp Logic (only if not paused)
                should_ramp_time = (secs_remaining_total % 2 == 0)
                can_ramp_value = (st.session_state.vpp_value < st.session_state.target_vpp)
                not_ramped_this_second = (st.session_state.last_ramp_second != secs_remaining_total)

                if should_ramp_time and can_ramp_value and not_ramped_this_second:
                     st.session_state.vpp_value += st.session_state.ramp_speed
                     st.session_state.vpp_value = round(st.session_state.vpp_value, 1)
                     # Display the message inside the placeholder
                     ramp_message_placeholder.success("Ramp 0.1 Vpp ↑", icon="⬆️") # <--- MODIFIED
                     st.session_state.last_ramp_second = secs_remaining_total
                else:
                     # Explicitly clear the placeholder if not ramping
                     ramp_message_placeholder.empty()

        #st.metric("Current Amplitude (Vpp)", f"{st.session_state.vpp_value:.1f}")

    else:
        # --- Timer Paused ---
        st.warning("PAUSED", icon="⏸️")
        if st.session_state.time_remaining_on_pause is not None:
             secs_remaining_total = int(st.session_state.time_remaining_on_pause)
             mm = secs_remaining_total // 60
             ss = secs_remaining_total % 60
             st.metric("Time Remaining (Paused)", f"{mm:02d}:{ss:02d}")
        else:
             st.metric("Time Remaining (Paused)", "--:--")

    # --- Display Vpp (Always visible when timer was running/paused) ---
    st.metric("Current Amplitude (Vpp)", f"{st.session_state.vpp_value:.1f}")

    # --- Action Buttons ---
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.paused:
            if st.button("Resume", key="resume_btn", use_container_width=True):
                # Calculate new end time based on paused duration
                if st.session_state.time_remaining_on_pause is not None:
                   resume_duration = datetime.timedelta(seconds=st.session_state.time_remaining_on_pause)
                   st.session_state.end_time = datetime.datetime.now() + resume_duration
                st.session_state.paused = False
                st.session_state.time_remaining_on_pause = None # Clear paused time
                st.rerun() # Immediately rerun to start timer
        else:
            if st.button("Pause", key="pause_btn", use_container_width=True):
                # Store remaining time *before* setting paused
                if st.session_state.end_time:
                   time_remaining = st.session_state.end_time - datetime.datetime.now()
                   st.session_state.time_remaining_on_pause = max(0, time_remaining.total_seconds()) # Avoid negative
                st.session_state.paused = True
                st.rerun() # Rerun to show paused state (no time.sleep)

    with col2:
        if st.button("Quit Session Early", key="quit_btn", type="primary", use_container_width=True):
            st.session_state.timer_running = False
            st.session_state.paused = False # Ensure not paused if quitting
            st.session_state.quit_early = True # Mark as quit

            # Prepare summary data for quit
            d = {
                'Status': ['Quit Early'],
                'Target Cycles': [st.session_state['Target number of cycles']],
                'Completed Cycles': [st.session_state['Number of cycles']], # Shows cycles completed *before* quit
                'Final Vpp': [round(st.session_state.vpp_value, 1)]
            }

            df = pd.DataFrame(data=d)
            st.session_state.session_summary = pd.DataFrame(d)
            @st.cache_data
            def convert_for_download(df):
                return df.to_csv().encode("utf-8")
            csv = convert_for_download(df)
            st.download_button('Download data summary',csv, file_name="TI_session_summary.csv")

            st.rerun() # Go to the 'not running' state to display summary


# --- Conditional Rerun Trigger ---

if st.session_state.timer_running and not st.session_state.paused:
    # (might need st.empty() for more complex message handling)
    time.sleep(1) # Pause slightly
    st.rerun()    # Trigger the next update cycle  # Trigger the next update cycle