#

#

# Timing Diagram
```text
    t (s) 0         1         2         3         4 

          |.........|.........|.........|.........|.........
Heater 
(example PID ~60% duty, 1s window)

          ██████···· ██████···· ██████···· ██████····

O₂ valve 
(Pulse 80% duty, 1s window)

          ████████·· ████████·· ████████·· ████████··      

CO₂ valve 
(Soft-start 20% duty for first 120 s)

          ██········ ██········ ██········ ██········ 
          (continues like this until t=120 s)

After t=120 s → CO₂ switches to normal pulse duty 
(example 35%)

          █████····· █████····· █████····· █████·····
```

# Gas Control Logic

| Gas          | Condition (relative to setpoint × threshold)                    | State                                   | Notes                                                    |
| ------------ | --------------------------------------------------------------- | --------------------------------------- | -------------------------------------------------------- |
| **O₂**       | `val > setpt × th_cont`                                         | **Continuous ON**                       | Purge N₂ strongly; highest priority. Forces CO₂ OFF.     |
|              | `val > setpt × th_puls` (but ≤ cont)                            | **Pulse** (default 80% duty, 1s window) | Short bursts to lower O₂ further.                        |
|              | `val > setpt × th_stop` (but ≤ pulse)                           | **OFF**                                 | Within safe band.                                        |
|              | `val ≤ setpt × th_stop`                                         | **OFF**                                 | Stable or below target.                                  |
| **CO₂**      | *Soft-start window* `t < 120 s` **AND** `val < setpt × th_puls` | **Pulse (20% duty)**                    | Gentle injection at boot to avoid overshoot.             |
|              | `t ≥ 120 s` **AND** `val < setpt × th_cont`                     | **Continuous ON**                       | Chamber strongly undersaturated.                         |
|              | `t ≥ 120 s` **AND** `val < setpt × th_puls` (but ≥ cont)        | **Pulse (e.g. 35% duty)**               | Configurable duty cycle after soft-start.                |
|              | `val < setpt × th_stop` (but ≥ pulse)                           | **OFF**                                 | Within safe band.                                        |
|              | `val ≥ setpt × th_stop`                                         | **OFF**                                 | Too high → injection disabled.                           |
| **Priority** | If **O₂ = Continuous ON**                                       | **CO₂ forced OFF**                      | Prevents simultaneous strong O₂ purge and CO₂ injection. |
