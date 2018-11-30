import os, re
import asyncio
import concurrent
class MoneroWalletCli(object):
    def __init__(self):
        self.regex = {
            "  (\w+)  Primary address": "address",
            "Opened wallet: (\w+)":"address",
            "Balance:\s+(\w+)":"balance",
            "unlocked balance: (\w+)":"unlocked_balance",
            "refresh-type = (\w+)": "refresh-type"
        }
        self.response = {
            "Enter the number corresponding to the language of your choice:": "1"
        }
        self.data={}
    async def start(self, network="stagenet", wallet="stagenet-wallet", password="123", loglevel=None, command_timeout=3):
        cwd = os.getcwd()
        self.command_timeout = command_timeout
        wallet_exe = os.path.join(cwd, 'monero-wallet-cli')
        params = [wallet_exe, "--"+network, "--password="+password]
        if os.path.isfile(wallet):
            params.append("--wallet="+wallet)
        else:
            params.append("--generate-new-wallet")
            params.append(wallet)
        if loglevel is not None:
            params.append("--log-file=/dev/stdout")
            params.append("--log-level="+str(loglevel))
        params.append("--use-english-language-names")
        print("OPEN  "+" ".join(params))
        self.p = await asyncio.create_subprocess_shell(" ".join(params),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT)
        print(f"PID {self.p.pid}")
        await self.run()
    
    def dump_data(self):
        for k,v in self.data.items():
            print(f"VAL  {k}={v}")

    async def terminate(self):
        pid = self.p.pid
        await self.exec("q")
        await self.sleep(5)
        print(f"KILL  {pid}")
        try:
            self.p.terminate()
        except: pass
        

    async def sleep(self, timeout):
        print(f"SLEEP  {timeout}")
        await asyncio.sleep(timeout)

    async def exec(self, command, eol="\n"):
        print("EXEC  "+command)
        self.p.stdin.write((command+eol).encode())
        await self.p.stdin.drain()
        
    async def run(self, command=None):
        try:
            res = None
            if command is not None:
                await self.exec(command)
            #out, err = await self.p.communicate(input=command.encode('utf-8') if command is not None else None)
            done = False
            while not done:
                commands = []
                buf = ''
                #async for line in self.p.stdout:
                while True:
                    try:
                        chunk = await asyncio.wait_for(self.p.stdout.read(1024), timeout=self.command_timeout)
                        chunk = chunk.decode('utf-8')
                        buf = buf+chunk
                        lines = buf.split('\n')
                        buf = lines[-1]
                        for i in range(0,len(lines)):
                    #for line in out.decode('utf-8').split('\n'):
                            #line = line.decode('utf-8')
                            line = lines[i].rstrip()
                            if len(line)>0:
                                print("READ  "+line)
                            command, brk = self.parse(line, i==len(lines)-1)
                            if command:
                                commands.append(command)
                            if brk:
                                break
                    except concurrent.futures._base.TimeoutError:
                        print(f"BRKT {self.command_timeout}")
                        break
                for command in commands:
                    await self.exec(command)
                else:
                    done = True
        except ValueError: 
            print("***")
            pass
        return res
        
    def parse(self, line, incomplete=False):
        command = None
        for rx,rk in self.regex.items():
            m = re.search(rx, line)  
            if m:
                self.data[rk] = m.group(1)
                print(f"DATA {rk}={self.data[rk]}")

        for rs in self.response.keys():
            if rs in line:
                command = self.response[rs]
                print(f"ANSW  {line} => <<<{command}>>>")

        if re.match("\[wallet (\w+)\]\:\n", line):
            print(f"BRKL <<<{line}>>>")
            return (None, True)

        return  (command, False)

async def main():
        #c = MoneroWalletCli(wallet="../../../_wallets/stagenet")
    #c.execute("address")
    #c.execute("q")

    w = MoneroWalletCli()
    await w.start(wallet="new-multi-1")
    await w.run("set ask-password 0")
    await w.run("set refresh-type fastsync")
    await w.run("balance")
    await w.terminate()
    w.dump_data()
    print("DONE")

if __name__=="__main__":
    asyncio.run(main())