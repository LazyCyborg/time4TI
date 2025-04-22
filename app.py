import streamlit as st
import pandas as pd
import datetime
import time

# --- Initialize Session State ---
# This needs to run first on every execution to ensure state exists
if 'Number of cycles' not in st.session_state:
    st.session_state['Number of cycles']= 0
    st.session_state['Target number of cycles'] = 1
if 'Frequency' not in st.session_state:
    st.session_state['Carrier frequency 1'] = 8000 # Default added
    st.session_state['Carrier frequency 2'] = 8130 # Default added
    st.session_state['Modulating frequency'] = 130 # Default added
if 'timer_running' not in st.session_state:
    st.session_state.timer_running = False
    st.session_state.end_time = None
    st.session_state.vpp_value = 0.0
    st.session_state.target_vpp = 4.0 # Default added
    st.session_state.last_ramp_second = -1
    st.session_state.ramp_speed = 0.1
if 'paused' not in st.session_state:
    st.session_state.paused = False
    st.session_state.time_remaining_on_pause = None # Store remaining seconds when paused
if 'quit_early' not in st.session_state:
    st.session_state.quit_early = False # Flag to indicate if session was quit
if 'session_summary' not in st.session_state:
    st.session_state.session_summary = None

if 'ramping_down' not in st.session_state:
    st.session_state.ramping_down = False
    st.session_state.ramp_down_tick_flag = False


st.title('Time4TI ⚡️')
st.markdown("Timer and logging app for classic temporal interference stimulation experiments. Currently only set to handle a two channel setup.")
with st.expander("ℹ️ Set up for classic TI with the Keysight EDU33212A", expanded=False):
    st.markdown("""
    1. Start the AWG and connect channel 1 and 2 to the appropriate inputs in the occiloscope or DS5
    2. Push the "Setup" button for channel 1 on the AWG, push "Output Load" and select "High Z"
    3. Push the "Dual channels" button for channel 1 and select "Ampl Cpl" and set amplitude coupling to "ON (make sure frequency coupling is disabled)"
    4. Push the "Parameters" button for channel 1 and select "Frequency".
    5. Push "Frequency" and set the frequency to the first carrier frequency to use (see reference for more details).
    6. Push "Amplitude" and set the amplitude to 0
    7. Push the "Setup" button for channel 2 and repeat step 2, 4, 5 and 6 for the second channel
    8. Push the "On/Off" button for channel 1 and 2 in order to start the stimulation.
    9. Set up the number of cycles, stimulation time and frequencies in the parameters below.
    10. Click "Start Session" in the interface (on this page).
    11. Push the "Parameters" button for channel 1 and increase/decrease the amplitude according to the Ramp ↑ / Ramp ↓ prompts shown in the interface.
    
    See:
    
    Missey, F., Acerbo, E., Dickey, A. S., Trajlinek, J., Studnička, O., Lubrano, C., de Araújo e Silva, M., Brady, E., Všianský, V., Szabo, J., Dolezalova, I., Fabo, D., Pail, M., Gutekunst, C.-A., Migliore, R., Migliore, M., Lagarde, S., Carron, R., Karimi, F., … Williamson, A. (2024). Non-invasive Temporal Interference Stimulation of the Hippocampus Suppresses Epileptic Biomarkers in Patients with Epilepsy: Biophysical Differences between Kilohertz and Amplitude Modulated Stimulation. https://doi.org/10.1101/2024.12.05.24303799
    
    for details on how to set carrier frequencies.
    
    See:
    
    https://simnibs.github.io/simnibs/build/html/tutorial/tes_flex_opt.html#tes-flex-opt
    
    for information on how to use SimNIBS 4.5 in order to estimate stimulation coordinates using the T1 MRI of a subject.
    
    See: 
    
    https://github.com/LazyCyborg/time4TI/blob/main/Find_closest_electrodes.ipynb
    
    for a simple way to use MNE-Python in order to find the closest electrode locations which is output by SimNIBS in subject space.
    
    """)
st.metric("Number of cycles", f"{st.session_state['Number of cycles']}")

ramp_message_placeholder = st.empty()

# --- Main Display Logic ---
if not st.session_state.timer_running and not st.session_state.ramping_down:
    # --- STATE: Timer Not Running (Initial or Finished) ---

    if st.session_state.session_summary is not None:
        st.write("--- Session Summary ---")
        if st.session_state.quit_early:
            st.warning("Session Quit Early!")
        else:
            st.success("Session Finished! ✅")

        final_vpp_display = 0.0 if not st.session_state.quit_early else round(st.session_state.vpp_value, 1)
        st.metric("Final Amplitude (Vpp)", f"{final_vpp_display:.1f}")

        if isinstance(st.session_state.session_summary, pd.DataFrame):
            st.dataframe(st.session_state.session_summary)
            try:
                @st.cache_data
                def convert_final_df_for_download(df_to_download):
                    return df_to_download.to_csv(index=False).encode("utf-8")
                csv_final = convert_final_df_for_download(st.session_state.session_summary)
                st.download_button(
                    'Download data summary',
                    csv_final,
                    file_name="TI_session_summary.csv",
                    key="final_download_key"
                )
            except Exception as e:
                 st.error(f"Failed to create download link: {e}")
        else:
            st.error("Session summary is not available for display or download.")

        st.divider()

        if st.button("Configure New Session", key="clear_summary"):
             st.session_state.end_time = None
             st.session_state.session_summary = None
             st.session_state.quit_early = False
             st.session_state.ramping_down = False
             st.session_state.vpp_value = 0.0
             st.rerun()

    elif st.session_state.end_time is None:
        st.info("Configure and press 'Start Session'.")
        with st.form("timer_form"):
            st.write("Configure the TI session:")
            minutes_val = st.slider(
                "Duration per cycle (minutes)",
                min_value=1, max_value=120, value=5, key="minutes_slider"
            )
            # Use .get() for robust access to state with defaults
            vpp_val = st.slider(
                "Target Amplitude (Vpp)",
                min_value=0.0, max_value=6.0, value=st.session_state.get('target_vpp', 4.0), step=0.1, key="vpp_slider"
            )

            carr_freq_1 = st.number_input(
                "Channel 1 carrier frequency (Hz)",
                min_value=0, max_value=20000, value=st.session_state.get('Carrier frequency 1', 8000), step=1, key="carr_1"
            )
            # <<< FIX: Remove immediate state update here >>>
            # st.session_state['Carrier frequency 1'] = carr_freq_1

            carr_freq_2 = st.number_input(
                "Channel 2 carrier frequency (Hz)",
                min_value=0, max_value=20000, value=st.session_state.get('Carrier frequency 2', 8130), step=1, key="carr_2"
            )

            # Calculate mod_freq from form inputs for display
            mod_freq = abs(carr_freq_2 - carr_freq_1) # Use abs() for correct calculation
            if carr_freq_2 - carr_freq_1 < 0:
                st.caption("Note: Modulating frequency calculated as absolute difference.") # More subtle warning

            st.write("Modulating frequency (Hz)", mod_freq) # Display calculated value

            target_n_cycles = st.number_input(
                "Set target number of cycles",
                 min_value=1, max_value=120, value=st.session_state.get('Target number of cycles', 1)
            )
            st.write("Selected number of cycles ", target_n_cycles)

            ramp_speed_input = st.number_input(
                "Ramp Speed (Vpp/prompt)",
                value=st.session_state.get('ramp_speed', 0.1),
                min_value=0.01, max_value=1.0, step=0.01, format="%.2f", key="ramp_speed_form"
            )

            # Update button logic
            updated = st.form_submit_button("Update Configuration", icon="🔄") # Renamed for clarity
            if updated:
                # <<< FIX: Explicitly set state on Update >>>
                st.session_state['Target number of cycles'] = target_n_cycles
                st.session_state.target_vpp = vpp_val
                st.session_state['Carrier frequency 1'] = carr_freq_1 # Set from form var
                st.session_state['Carrier frequency 2'] = carr_freq_2 # Set from form var
                st.session_state['Modulating frequency'] = abs(carr_freq_2 - carr_freq_1) # Set calculated value
                st.session_state.ramp_speed = ramp_speed_input
                st.success("Configuration updated!") # Give feedback

            st.divider()
            st.text('Ramp ↑ will appear on even seconds remaining.')
            st.text('Ramp ↓ will appear every other second during ramp-down.')
            submitted = st.form_submit_button("Start Session", icon="🚀")

            if submitted:
                # <<< FIX: Explicitly set ALL state from form vars on Start >>>
                st.session_state['Target number of cycles'] = target_n_cycles
                st.session_state.target_vpp = vpp_val
                st.session_state['Carrier frequency 1'] = carr_freq_1
                st.session_state['Carrier frequency 2'] = carr_freq_2
                st.session_state['Modulating frequency'] = abs(carr_freq_2 - carr_freq_1) # Use abs()
                st.session_state.ramp_speed = ramp_speed_input

                # Initialize runtime state
                st.session_state.timer_running = True
                st.session_state.ramping_down = False
                st.session_state.paused = False
                st.session_state.quit_early = False
                st.session_state.session_summary = None
                duration = datetime.timedelta(minutes=minutes_val)
                st.session_state.end_time = datetime.datetime.now() + duration
                st.session_state.vpp_value = 0.0
                st.session_state.last_ramp_second = -1
                st.session_state.ramp_down_tick_flag = False
                st.rerun()

elif st.session_state.timer_running or st.session_state.ramping_down:
    # --- STATE: Active Session (Timer Running OR Ramping Down) ---

    st.metric("Current Amplitude (Vpp)", f"{st.session_state.vpp_value:.1f}")
    secs_remaining_total = 0

    if st.session_state.paused:
        st.warning("PAUSED", icon="⏸️")
        if st.session_state.time_remaining_on_pause is not None:
             secs_remaining_total = int(st.session_state.time_remaining_on_pause)
             mm = secs_remaining_total // 60
             ss = secs_remaining_total % 60
             st.metric("Time Remaining (Paused)", f"{mm:02d}:{ss:02d}")
        elif st.session_state.ramping_down:
             st.metric("Time Remaining", "N/A (Paused during Ramp Down)")
        else:
             st.metric("Time Remaining (Paused)", "--:--")
        ramp_message_placeholder.empty()

    else: # Not Paused
        if st.session_state.ramping_down:
            st.info("Ramping Down...")
            if st.session_state.ramp_down_tick_flag:
                st.session_state.vpp_value -= st.session_state.ramp_speed
                st.session_state.vpp_value = round(max(0.0, st.session_state.vpp_value), 1)
                ramp_message_placeholder.info(f"Ramp {st.session_state.ramp_speed:.2f} Vpp ↓", icon="⬇️")
            else:
                ramp_message_placeholder.empty()

            st.session_state.ramp_down_tick_flag = not st.session_state.ramp_down_tick_flag

            if st.session_state.vpp_value <= 0.0:
                st.session_state.ramping_down = False
                st.session_state.quit_early = False
                st.session_state['Number of cycles'] += 1
                # <<< FIX: Read directly from session state for summary >>>
                d_complete = {
                    'Status': ['Completed'],
                    'Target Cycles': [st.session_state['Target number of cycles']],
                    'Completed Cycles': [st.session_state['Number of cycles']],
                    'Carrier frequency 1': [st.session_state['Carrier frequency 1']],
                    'Carrier frequency 2': [st.session_state['Carrier frequency 2']],
                    'Modulating frequency': [st.session_state['Modulating frequency']],
                    'Target Vpp': [st.session_state.target_vpp],
                    'Final Vpp': [0.0]
                }
                st.session_state.session_summary = pd.DataFrame(d_complete)
                ramp_message_placeholder.empty()
                st.rerun()

        elif st.session_state.timer_running:
            if st.session_state.end_time is None:
                st.error("Error: Timer running but end time not set.")
                st.session_state.timer_running = False
                st.rerun()
            else:
                time_remaining = st.session_state.end_time - datetime.datetime.now()
                secs_remaining_total = int(time_remaining.total_seconds())

                if secs_remaining_total < 0:
                    st.session_state.timer_running = False
                    if st.session_state.vpp_value > 0:
                        st.session_state.ramping_down = True
                        st.session_state.last_ramp_second = -1
                        st.session_state.ramp_down_tick_flag = True
                        ramp_message_placeholder.empty()
                        st.rerun()
                    else:
                        st.session_state.ramping_down = False
                        st.session_state.quit_early = False
                        st.session_state['Number of cycles'] += 1
                        # <<< FIX: Read directly from session state for summary >>>
                        d_finish_vpp0 = {
                            'Status': ['Completed (Vpp=0 at end)'],
                            'Target Cycles': [st.session_state['Target number of cycles']],
                            'Completed Cycles': [st.session_state['Number of cycles']],
                            'Carrier frequency 1': [st.session_state['Carrier frequency 1']],
                            'Carrier frequency 2': [st.session_state['Carrier frequency 2']],
                            'Modulating frequency': [st.session_state['Modulating frequency']],
                            'Target Vpp': [st.session_state.target_vpp],
                            'Final Vpp': [0.0]
                        }
                        st.session_state.session_summary = pd.DataFrame(d_finish_vpp0)
                        # No need for separate df/download here, summary display handles it
                        ramp_message_placeholder.empty()
                        st.rerun()

                else:
                    mm = secs_remaining_total // 60
                    ss = secs_remaining_total % 60
                    st.metric("Time Remaining", f"{mm:02d}:{ss:02d}")

                    # Ramp Up Logic
                    should_ramp_time = (secs_remaining_total % 2 == 0)
                    can_ramp_value = (st.session_state.vpp_value < st.session_state.target_vpp)
                    not_ramped_this_second = (st.session_state.last_ramp_second != secs_remaining_total)

                    if should_ramp_time and can_ramp_value and not_ramped_this_second:
                         st.session_state.vpp_value += st.session_state.ramp_speed
                         st.session_state.vpp_value = round(min(st.session_state.vpp_value, st.session_state.target_vpp), 1)
                         ramp_message_placeholder.success(f"Ramp {st.session_state.ramp_speed:.2f} Vpp ↑", icon="⬆️")
                         st.session_state.last_ramp_second = secs_remaining_total
                    else:
                         ramp_message_placeholder.empty()

    # --- Action Buttons ---
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.paused:
            if st.button("Resume", key="resume_btn", use_container_width=True):
                if st.session_state.timer_running and not st.session_state.ramping_down and st.session_state.time_remaining_on_pause is not None:
                   resume_duration = datetime.timedelta(seconds=st.session_state.time_remaining_on_pause)
                   st.session_state.end_time = datetime.datetime.now() + resume_duration
                st.session_state.paused = False
                st.session_state.time_remaining_on_pause = None
                st.rerun()
        else:
            if st.session_state.timer_running or st.session_state.ramping_down:
                if st.button("Pause", key="pause_btn", use_container_width=True):
                    if st.session_state.timer_running and not st.session_state.ramping_down and st.session_state.end_time:
                       time_remaining = st.session_state.end_time - datetime.datetime.now()
                       st.session_state.time_remaining_on_pause = max(0, time_remaining.total_seconds())
                    else:
                        st.session_state.time_remaining_on_pause = None
                    st.session_state.paused = True
                    st.rerun()

    with col2:
        if st.session_state.timer_running or st.session_state.ramping_down:
            if st.button("Quit Session Early", key="quit_btn", type="primary", use_container_width=True):
                final_vpp_quit = round(st.session_state.vpp_value, 1)
                st.session_state.timer_running = False
                st.session_state.ramping_down = False
                st.session_state.paused = False
                st.session_state.quit_early = True

                # <<< FIX: Read directly from session state for summary >>>
                # (This part was already correct in the previous version, just confirming)
                d_quit = {
                    'Status': ['Quit Early'],
                    'Target Cycles': [st.session_state['Target number of cycles']],
                    'Completed Cycles': [st.session_state['Number of cycles']],
                    'Carrier frequency 1': [st.session_state['Carrier frequency 1']],
                    'Carrier frequency 2': [st.session_state['Carrier frequency 2']],
                    'Modulating frequency': [st.session_state['Modulating frequency']],
                    'Target Vpp': [st.session_state.target_vpp],
                    'Final Vpp': [final_vpp_quit]
                }
                st.session_state.session_summary = pd.DataFrame(d_quit)
                # No need for separate df/download here, summary display handles it
                ramp_message_placeholder.empty()
                st.rerun()

# --- Conditional Rerun Trigger ---
if (st.session_state.timer_running or st.session_state.ramping_down) and not st.session_state.paused:
    time.sleep(1)
    st.rerun()