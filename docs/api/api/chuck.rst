ChucK Class
===========

.. currentmodule:: numchuck

.. autoclass:: ChucK
   :members:
   :undoc-members:
   :show-inheritance:

   .. rubric:: Initialization

   .. automethod:: __init__
   .. automethod:: init
   .. automethod:: start

   .. rubric:: Code Compilation

   .. automethod:: compile_code
   .. automethod:: compile_file

   .. rubric:: Audio Processing

   .. automethod:: run

   .. rubric:: Global Variables

   .. automethod:: set_global_int
   .. automethod:: set_global_float
   .. automethod:: set_global_string
   .. automethod:: get_global_int
   .. automethod:: get_global_float
   .. automethod:: get_global_string

   .. rubric:: Global Arrays

   .. automethod:: set_global_int_array
   .. automethod:: set_global_float_array
   .. automethod:: set_global_int_array_value
   .. automethod:: set_global_float_array_value
   .. automethod:: set_global_associative_int_array_value
   .. automethod:: set_global_associative_float_array_value
   .. automethod:: get_global_int_array
   .. automethod:: get_global_float_array
   .. automethod:: get_global_int_array_value
   .. automethod:: get_global_float_array_value
   .. automethod:: get_global_associative_int_array_value
   .. automethod:: get_global_associative_float_array_value

   .. rubric:: Global UGens

   .. automethod:: get_ugen_samples
   .. automethod:: add_tap
   .. automethod:: remove_tap
   .. automethod:: list_taps

   .. rubric:: Global Events

   .. automethod:: signal_global_event
   .. automethod:: broadcast_global_event
   .. automethod:: listen_for_global_event
   .. automethod:: stop_listening_for_global_event

   .. rubric:: Shred Management

   .. automethod:: remove_shred
   .. automethod:: remove_all_shreds
   .. automethod:: replace_shred
   .. automethod:: get_all_shred_ids
   .. automethod:: get_ready_shred_ids
   .. automethod:: get_blocked_shred_ids
   .. automethod:: get_last_shred_id
   .. automethod:: get_next_shred_id
   .. automethod:: get_shred_info
   .. automethod:: abort_current_shred
   .. automethod:: subscribe_shred_watcher
   .. automethod:: remove_shred_watcher

   .. rubric:: VM Control

   .. automethod:: clear_vm
   .. automethod:: reset_shred_id
   .. automethod:: set_adaptive
   .. automethod:: get_adaptive

   .. rubric:: Status Methods

   .. automethod:: is_init
   .. automethod:: vm_running
   .. automethod:: now

   .. rubric:: Static Methods

   .. automethod:: version
   .. automethod:: int_size
   .. automethod:: num_vms
