import os
from datetime import datetime
import asyncio
import yaml


async def make_async(func, *args):
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(None, func, *args)
    return res


def read_config(fn='./configs/config.yml'):
    config = None
    if not os.path.exists(fn):
        raise ValueError(f"Cannot open config file: {fn}")
    
    with open(fn, 'r') as f:
        config = yaml.safe_load(f)
    return config


def create_pine_script(df_history, side_key='side', cost_key='cost', time_key='executed_at', script_title="History", max_lines=200):
    lines = [
        "// @version=4\n\nstudy(\"{}\", overlay=true, max_labels_count=500)\n".format(script_title),
    ]

    count = 0
    for i, row in df_history.iterrows():

        count += 1
        if count > max_lines:
            break

        if row[side_key] == "sell":
            color = "color.red"
            text = "Sell\\n"
            style = 'label.style_labeldown'
            yloc = 'yloc.abovebar'
        elif row[side_key] == "buy":
            color = "color.green"
            text = "Buy\\n"
            style = 'label.style_labelup'
            yloc = 'yloc.belowbar'
        text += "{0:.0f}".format(row[cost_key])

        time = datetime.fromtimestamp(row[time_key]/1000)
        line = 'label.new(timestamp("GMT+9",{time}),close,xloc=xloc.bar_time,' \
               'yloc={yloc},text="{text}",style={style},color={color})' \
            .format(time=",".join(map(str, [time.year, time.month, time.day, time.hour, time.minute])),
                    text=text, color=color, style=style, yloc=yloc)
        lines.append(line)

    return "\n".join(lines)